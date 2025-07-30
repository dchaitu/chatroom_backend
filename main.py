import hashlib
import uuid
from datetime import datetime
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from sqlalchemy.orm import Session
from starlette import status
from botocore.exceptions import ClientError, ValidationError
import boto3
import json

from constants import secret_key
from models import User, Room, Base, Message, Connection
from database import engine, get_db
from schemas import (
    UserCreate,
    RoomCreate,
    UserLogin,
    MessageSchema,
    RoomSchema,
    UserSchema,
    UserRoomSchema,
    SendMessage,
    UsernameSchema,
    RoomIdSchema,
)

app = FastAPI()
Base.metadata.create_all(bind=engine)
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
API_GATEWAY_ENDPOINT = (
    "https://c4plozmo3f.execute-api.us-east-1.amazonaws.com/production/"
)
apigw_management_client = boto3.client(
    "apigatewaymanagementapi", endpoint_url=API_GATEWAY_ENDPOINT
)


async def verify_recaptcha(token: str) -> bool:
    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {
        "secret": secret_key,
        "response": token,
    }
    response = requests.post(url, data=data)
    result = response.json()
    return result["success"]


@app.post("/create_room")
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == room.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_room = db.query(Room).filter(Room.room_id == room.room_id).first()
    if existing_room:
        raise HTTPException(status_code=400, detail="Room already exists")

    new_room = Room(room_id=room.room_id, room_name=room.room_name)

    try:
        user.rooms.append(new_room)
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        return {"message": f"Room created successfully: {new_room.room_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create room")

def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@app.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(user_info: UserCreate, db: Session = Depends(get_db)):
    is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
    if not is_valid_captcha:
        raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

    user = db.query(User).filter(User.username == user_info.username).first()
    if user:
        return {"message": "User already exists"}

    hashed_password = hash_password(user_info.password)
    new_user = User(
        username=user_info.username,
        password=hashed_password,
        fullname=user_info.fullname,
        email=user_info.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User created successfully: {new_user.username}"}


@app.post("/login/")
async def login(user_info: UserLogin, db: Session = Depends(get_db)):
    is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
    if not is_valid_captcha:
        raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

    user = db.query(User).filter(User.username == user_info.username).first()
    print(f"user {user}")
    hashed_password = hash_password(user_info.password)
    if user:
        actual_password = user.password
        if actual_password == hashed_password:
            return {
                "message": f"User logged in successfully: {user.username}",
                "status_code": 200,
            }
        else:
            return {"message": "Wrong password", "status_code": 401}

    return {"message": "User not found", "status_code": 404}


@app.post("/user/", response_model=UserSchema)
async def get_user_profile(user_info: UsernameSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/websocket/send_message/")
async def send_message_in_room(message: MessageSchema, db: Session = Depends(get_db)):
    sender = db.query(User).filter(User.username == message.username).first()
    room = db.query(Room).filter(Room.room_id == message.room_id).first()
    sender_is_in_room = (
        db.query(User)
        .filter(User.rooms.any(room_id=message.room_id))
        .filter(User.username == message.username)
        .first()
    )
    if not sender:
        return {"message": "Sender not exists"}
    if not room:
        return {"message": "Room does not exist"}
    if not sender_is_in_room:
        return {"message": "Sender is not in the room"}

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

    connections = db.query(Connection).filter(Connection.room_id == message.room_id).all()
    message_data = {
        "message_id": new_message.message_id,
        "content": new_message.content,
        "username": new_message.username,
        "room_id": new_message.room_id,
        "timestamp": new_message.timestamp.isoformat(),
    }

    for connection in connections:
        try:
            apigw_management_client.post_to_connection(
                Data=json.dumps(message_data), ConnectionId=connection.connection_id
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                db.delete(connection)
                db.commit()
            else:
                print(f"Error sending message to {connection.connection_id}: {e}")

    return {"message": f"Message sent successfully: {new_message.message_id}"}


@app.post("/rooms/", response_model=list[RoomSchema])
async def get_user_rooms(user_details: UsernameSchema, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username == user_details.username).all()
    user_rooms = []
    for user in users:
        for room in user.rooms:
            user_rooms.append(room.room_id)
    if len(user_rooms) == 0:
        return {"message": "Room does not exist"}

    return db.query(Room).filter(Room.room_id.in_(user_rooms)).all()


@app.post("/join_room/")
async def join_room(join_room: UserRoomSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == join_room.username).first()
    room = db.query(Room).filter(Room.room_id == join_room.room_id).first()

    if not user:
        return {"message": "User does not exist"}
    if not room:
        return {"message": "Room does not exist"}
    user.rooms.append(room)
    db.commit()
    return {
        "message": f"{user.username} is joined in the room {room.room_name}",
        "status_code": 200,
    }


@app.post("/leave_room/")
async def user_leave_room(leave_room: UserRoomSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == leave_room.username).first()
    room = db.query(Room).filter(Room.room_id == leave_room.room_id).first()

    if not user:
        return {"message": "User does not exist"}
    if not room:
        return {"message": "Room does not exist"}
    user.rooms.remove(room)
    db.commit()
    return {"message": f"{user.username} has left the room {room.room_name}"}


@app.post("/rooms/messages/", response_model=list[MessageSchema])
async def get_all_messages_in_room(room: RoomIdSchema, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.room_id == room.room_id).all()
    return messages


def websocket_connect(event, context):
    db = next(get_db())
    connection_id = event["requestContext"]["connectionId"]
    username = event.get("queryStringParameters", {}).get("username")
    room_id = event.get("queryStringParameters", {}).get("room_id")

    if not username or not room_id:
        return {"statusCode": 400, "body": "Missing username or room_id"}

    user = db.query(User).filter(User.username == username).first()
    room = db.query(Room).filter(Room.room_id == room_id).first()

    if not user:
        return {"message": "User does not exist", "statusCode": 400}
    if not room:
        return {"message": "Room does not exist", "statusCode": 400}

    user_in_room = (
        db.query(User)
        .filter(User.rooms.any(room_id=room_id))
        .filter(User.username == username)
        .first()
    )
    if not user_in_room:
        return {"statusCode": 403, "body": "User not in room"}

    existing_connection = db.query(Connection).filter(Connection.username == username,
                                                      Connection.room_id == room_id).first()
    if existing_connection:
        db.delete(existing_connection)
        db.commit()


    new_connection = Connection(
        connection_id=connection_id, username=username, room_id=room_id
    )
    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)
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
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid or missing message body"})}

    try:
        print("Raw body before parsing:", body)
        data = json.loads(body)
        print("Parsed data:", data)
    except json.JSONDecodeError as e:
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid JSON format", "error": str(e), "raw_body": body})}

    action = data.get("action")
    if action != "sendmessage":
        return {"statusCode": 400, "body": json.dumps({"message": "Invalid action"})}

    message_data = {k: v for k, v in data.items() if k != "action"}
    try:
        message = MessageSchema(**message_data)
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"message": "Validation error", "details": e.errors()})}

    sender = db.query(User).filter(User.username == message.username).first()
    room = db.query(Room).filter(Room.room_id == message.room_id).first()
    sender_is_in_room = db.query(User).filter(User.rooms.any(room_id=message.room_id)).filter(User.username == message.username).first()

    if not sender:
        return {"statusCode": 404, "body": json.dumps({"message": "Sender does not exist"})}
    if not room:
        return {"statusCode": 404, "body": json.dumps({"message": "Room does not exist"})}
    if not sender_is_in_room:
        return {"statusCode": 403, "body": json.dumps({"message": "Sender is not in room"})}

    new_message = Message(
        message_id=str(uuid.uuid4()),
        content=message.content,
        username=message.username,
        room_id=message.room_id,
        timestamp=message.timestamp or datetime.now(datetime.UTC)
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    connections = db.query(Connection).filter(Connection.room_id == message.room_id).all()
    print(f"Found connections: {len(connections)} for room {message.room_id}")  # Add this
    message_data = {
        "message_id": new_message.message_id,
        "content": new_message.content,
        "username": new_message.username,
        "room_id": new_message.room_id,
        "timestamp": new_message.timestamp.isoformat()
    }

    for connection in connections:
        try:
            print(f"Broadcasting to connection: {connection.connection_id}")
            apigw_management_client.post_to_connection(
                Data=json.dumps(message_data),
                ConnectionId=connection.connection_id
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'GoneException':
                db.delete(connection)
                db.commit()
                print(f"Removed stale connection: {connection.connection_id}")
            else:
                print(f"Error broadcasting to {connection.connection_id}: {e}")

    return {"statusCode": 200, "body": json.dumps({"message": f"Message sent successfully: {new_message.message_id}"})}

def handler(event, context):
    route_key = event.get("requestContext", {}).get("routeKey")
    if route_key == "$connect":
        return websocket_connect(event, context)
    elif route_key == "$disconnect":
        return websocket_disconnect(event, context)
    elif route_key == "sendmessage":  # Adjust based on your route key
        return websocket_send_message(event, context)
    else:
        # Delegate HTTP events to Mangum
        return Mangum(app)(event, context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
