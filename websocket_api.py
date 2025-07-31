import json
import uuid
from datetime import datetime

import boto3
from database import get_db

API_GATEWAY_ENDPOINT = 'https://c4plozmo3f.execute-api.us-east-1.amazonaws.com/production/@connections'
apigw_management_client = boto3.client('apigatewaymanagementapi', endpoint_url=API_GATEWAY_ENDPOINT)

dynamodb = boto3.resource("dynamodb")
user_table = dynamodb.Table("User")
room_table = dynamodb.Table("Room")
connection_table = dynamodb.Table("Connection")
message_table = dynamodb.Table("Message")


def websocket_connect(event, context):
    db = get_db()
    # ConnectionModel = db['connections']
    connection_id = event["requestContext"]["connectionId"]
    username = event.get("queryStringParameters", {}).get("username")
    room_id = event.get("queryStringParameters", {}).get("room_id")

    if not username or not room_id:
        return {"statusCode": 400, "body": "Missing username or room_id"}

    # Check if user and room exist
    user = user_table.get_item(Key={"username": username}).get("Item")
    room = room_table.get_item(Key={"room_id": room_id}).get("Item")

    if not user or not room:
        return {"statusCode": 404, "body": "User or Room not found"}

    # Save connection
    connection_table.put_item(Item={
        "connection_id": connection_id,
        "username": username,
        "room_id": room_id,
        "connected_at": datetime.utcnow().isoformat()
    })

    return {"statusCode": 200, "body": "Connected"}

def websocket_disconnect(event, context):
    connection_id = event["requestContext"]["connectionId"]
    connection_table.delete_item(Key={"connection_id": connection_id})
    return {"statusCode": 200, "body": "Disconnected"}

def websocket_send_message(event, context):
    body = json.loads(event.get("body", "{}"))
    action = body.get("action")

    if action != "sendmessage":
        return {"statusCode": 400, "body": "Invalid action"}

    content = body.get("content")
    username = body.get("username")
    room_id = body.get("room_id")
    timestamp = datetime.utcnow().isoformat()

    if not all([content, username, room_id]):
        return {"statusCode": 400, "body": "Missing fields"}

    # Save message
    message_id = str(uuid.uuid4())
    message_item = {
        "message_id": message_id,
        "content": content,
        "username": username,
        "room_id": room_id,
        "timestamp": timestamp
    }
    message_table.put_item(Item=message_item)

    # Broadcast to all connections in room
    connections = connection_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("room_id").eq(room_id)
    )["Items"]

    for conn in connections:
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=conn["connection_id"],
                Data=json.dumps(message_item)
            )
        except Exception as e:
            print(f"Failed to send to {conn['connection_id']}: {e}")

    return {"statusCode": 200, "body": "Message sent"}

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