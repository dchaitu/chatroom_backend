import json
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, ValidationError
from models import Connection, User, Room, Message
from database import get_db

API_GATEWAY_ENDPOINT = 'https://c4plozmo3f.execute-api.us-east-1.amazonaws.com/production/@connections'
apigw_management_client = boto3.client('apigatewaymanagementapi', endpoint_url=API_GATEWAY_ENDPOINT)
from schemas import MessageSchema

def websocket_connect(event, context):
    db = next(get_db())
    connection_id = event["requestContext"]["connectionId"]
    username = event.get("queryStringParameters", {}).get("username")
    room_id = event.get("queryStringParameters", {}).get("room_id")

    if not username or not room_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing username or room_id"}),
        }

    user = db.query(User).filter(User.username == username).first()
    room = db.query(Room).filter(Room.room_id == room_id).first()

    if not user:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "User does not exist"}),
        }
    if not room:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Room does not exist"}),
        }

    user_in_room = (
        db.query(User)
        .filter(User.rooms.any(room_id=room_id))
        .filter(User.username == username)
        .first()
    )
    if not user_in_room:
        return {"statusCode": 403, "body": json.dumps({"message": "User not in room"})}

    existing_connection = (
        db.query(Connection)
        .filter(Connection.username == username, Connection.room_id == room_id)
        .first()
    )
    if existing_connection:
        existing_connection.connection_id = connection_id
    else:
        existing_connection = Connection(
            username=username,
            room_id=room_id,
            connection_id=connection_id
        )
        db.add(existing_connection)
    # db.add(new_connection)
    db.commit()
    db.refresh(existing_connection)
    print(f"Connected: {username} to room {room_id} with connection_id {connection_id}")
    return {"statusCode": 200, "body": json.dumps({"message": "Connected"})}


def websocket_disconnect(event, context):
    db = next(get_db())
    connection_id = event["requestContext"]["connectionId"]
    connection = (
        db.query(Connection).filter(Connection.connection_id == connection_id).first()
    )
    if connection:
        db.delete(connection)
        db.commit()
    return {"statusCode": 200, "body": json.dumps({"message": "Disconnected"})}


def websocket_send_message(event, context):
    db = next(get_db())
    print("Received event:", event)
    body = event.get("body")
    if not body or not isinstance(body, str) or body.strip() == "":
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid or missing message body"}),
        }

    try:
        print("Raw body before parsing:", body)
        data = json.loads(body)
        print("Parsed data:", data)
    except json.JSONDecodeError as e:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "Invalid JSON format", "error": str(e), "raw_body": body}
            ),
        }

    action = data.get("action")
    if action != "sendmessage":
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid action"})}

    message_data = {k: v for k, v in data.items() if k != "action"}
    try:
        message = MessageSchema(**message_data)
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Validation error", "details": e.errors()}),
        }

    sender = db.query(User).filter(User.username == message.username).first()
    room = db.query(Room).filter(Room.room_id == message.room_id).first()
    sender_is_in_room = (
        db.query(User)
        .filter(User.rooms.any(room_id=message.room_id))
        .filter(User.username == message.username)
        .first()
    )

    if not sender:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Sender does not exist"}),
        }
    if not room:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Room does not exist"}),
        }
    if not sender_is_in_room:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Sender is not in room"}),
        }

    new_message = Message(
        message_id=str(uuid.uuid4()),
        content=message.content,
        username=message.username,
        room_id=message.room_id,
        timestamp=message.timestamp or datetime.now(datetime.UTC),
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    connections = (
        db.query(Connection).filter(Connection.room_id == message.room_id).all()
    )
    print(f"Found connections: {len(connections)} for room {message.room_id}")
    connections = db.query(Connection).filter(Connection.room_id == message.room_id).all()
    print(f"Found connections: {len(connections)} for room {message.room_id}")
    print(f"Sender: {sender}, Room: {room}, Sender in room: {sender_is_in_room}")
    print(f"Connections: {len(connections)}:- {connections} for room {message.room_id} ")
    print("All connections for room:", [c.connection_id for c in connections])

    message_data = {
        "message_id": new_message.message_id,
        "content": new_message.content,
        "username": new_message.username,
        "room_id": new_message.room_id,
        "timestamp": new_message.timestamp.isoformat(),
    }

    for connection in connections:
        try:
            print(f"Broadcasting to connection: {connection.connection_id}")
            response = apigw_management_client.post_to_connection(
                Data=json.dumps(message_data), ConnectionId=connection.connection_id
            )
            print(f"Sent message to {connection.connection_id}: {response}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                db.delete(connection)
                db.commit()
                print(f"Removed stale connection: {connection.connection_id}")
            else:
                print(f"Error broadcasting to {connection.connection_id}: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Message sent successfully: {new_message.message_id}"}
        ),
    }


def handler(event, context):
    route_key = event.get("requestContext", {}).get("routeKey")
    if route_key == "$connect":
        return websocket_connect(event, context)
    elif route_key == "$disconnect":
        return websocket_disconnect(event, context)
    elif route_key == "sendmessage":
        return websocket_send_message(event, context)
    else:
        return {"statusCode": 400, "body": json.dumps({"message": "Unsupported route"})}
