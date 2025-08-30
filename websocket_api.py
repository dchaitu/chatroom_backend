import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
import boto3
from dateutil.parser import isoparse
import websockets

API_GATEWAY_ENDPOINT = 'https://c4plozmo3f.execute-api.us-east-1.amazonaws.com/production'
# LOCAL_ENDPOINT = 'http://0.0.0.0:8080'
apigw_management_client = boto3.client('apigatewaymanagementapi', endpoint_url=API_GATEWAY_ENDPOINT)

MODE = os.getenv("APP_MODE", "local")
LOCAL_ENDPOINT = "http://localhost:8000"

# ---- DYNAMODB ----
if MODE == "local":
    dynamodb = boto3.resource("dynamodb", endpoint_url=LOCAL_ENDPOINT)
else:
    dynamodb = boto3.resource("dynamodb")

user_table = dynamodb.Table("User")
room_table = dynamodb.Table("Room")
connection_table = dynamodb.Table("Connection")
message_table = dynamodb.Table("Message")

active_connections = {}
apigw_client = None
if MODE == "aws":
    apigw_client = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=API_GATEWAY_ENDPOINT
    )

def websocket_connect(event, context):
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
        "connected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+0000")
    })

    return {"statusCode": 200, "body": "Connected"}

def websocket_disconnect(event, context):
    connection_id = event["requestContext"]["connectionId"]
    connection_table.delete_item(Key={"connection_id": connection_id})
    return {"statusCode": 200, "body": "Disconnected"}

async def websocket_send_message(event, context):
    body = json.loads(event.get("body", "{}"))
    print("websocket_send_message body is proper", body)
    action = body.get("action")

    if action != "sendmessage":
        return {"statusCode": 400, "body": "Invalid action"}

    content = body.get("content")
    username = body.get("username")
    room_id = body.get("room_id")
    timestamp = body.get("timestamp",datetime.now(timezone.utc).isoformat())
    if timestamp is not None:
        try:
            # Parse incoming string to datetime object
            timestamp_dt = isoparse(timestamp)
        except Exception:
            timestamp_dt = datetime.now(timezone.utc)
    else:
        timestamp_dt = datetime.now(timezone.utc)
    print("websocket_send_message timestamp is proper",timestamp)
    if not all([content, username, room_id]):
        return {"statusCode": 400, "body": "Missing fields"}

    # Save message
    message_id = str(uuid.uuid4())
    message_item = {
        "message_id": message_id,
        "content": content,
        "username": username,
        "room_id": room_id,
        "timestamp": timestamp_dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    }
    message_table.put_item(Item=message_item)

    # Broadcast to all connections in room
    connections = connection_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("room_id").eq(room_id)
    )["Items"]
    connections = connection_table.scan()["Items"]
    for conn_ws, conn_id in active_connections.items():
        if any([conn["room_id"] == room_id for conn in connections]):
            await conn_ws.send(json.dumps(message_item))

    print("websocket_send_message connections is proper",connections)
    for conn in connections:
        try:
            apigw_management_client.post_to_connection(
                ConnectionId=conn["connection_id"],
                Data=json.dumps(message_item)
            )
        except Exception as e:
            print(f"Failed to send to {conn['connection_id']}: {e}")

    return {"statusCode": 200, "body": "Message sent"}

async def handler(event, context):
    print("Raw event:", event)
    route_key = event.get("requestContext", {}).get("routeKey")
    if route_key == "$connect":
        return websocket_connect(event, context)
    elif route_key == "$disconnect":
        return websocket_disconnect(event, context)
    elif route_key == "sendmessage":
        return websocket_send_message(event, context)
    else:
        return {"statusCode": 400, "body": json.dumps({"message": "Unsupported route"})}