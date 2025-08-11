print("Starting", flush=True)
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from datetime import datetime, timedelta, UTC
import os
import requests
import boto3
import jwt


print("External Imports", flush=True)
from models import User, Room, Message, Connection
from schemas import UserCreate, RoomCreate, UserLogin, MessageSchema, RoomSchema, UserRoomSchema

print("Internal Imports", flush=True)
dynamodb = boto3.client('dynamodb')

print("List Dynamodb Tables", flush=True)
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    '*'
]
JWT_SECRET = os.environ.get('JWT_SECRET','p1beyVW)E>b{1gya{,I+yd]>DfN/\9#*')
secret_key = os.environ.get('RECAPTCHA_SECRET_KEY')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_access_token(username: str, expires_delta: timedelta = None):
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def verify_recaptcha(token: str) -> bool:
    if token == "test-token":
        return True

    url = "https://www.google.com/recaptcha/api/siteverify"
    data = {
        "secret": secret_key,
        "response": token,
    }
    response = requests.post(url, data=data)
    result = response.json()
    print(result)
    return result["success"]


@app.post("/register/", status_code=201)
def register_user(user_info: UserCreate):
    print(f"Received registration request: {user_info}", flush=True)

    # Skip reCAPTCHA for testing - add back later
    # is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
    # if not is_valid_captcha:
    #     raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

    try:
        existing_user = User.get(user_info.username)
        return {"message": "User already exists"}
    except User.DoesNotExist:
        pass

    hashed_password = hash_password(user_info.password)
    user = User(
        username=user_info.username,
        password=hashed_password,
        fullname=user_info.fullname,
        email=user_info.email,
        rooms=[]
    )
    user.save()
    return {"message": f"User created successfully: {user_info.username}"}


@app.post("/login/", status_code=200)
def login(user_info: UserLogin):
    print(f"Received login request: {user_info}")

    # Skip reCAPTCHA for testing - add back later
    # is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
    # if not is_valid_captcha:
    #     raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

    try:
        user = User.get(user_info.username)
    except User.DoesNotExist:
        return {"message": "Invalid credentials", "status_code": 401}

    if user.password != hash_password(user_info.password):
        return {"message": "Invalid credentials", "status_code": 401}

    access_token = create_access_token(user_info.username)
    refresh_token = create_access_token(user_info.username, timedelta(days=30))
    print("access_token ", access_token)
    print("refresh_token ", refresh_token)
    return {
        "message": f"User logged in successfully: {user_info.username}",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@app.get("/user/{username}")
async def get_user_profile(username: str):
    try:
        user = User.get(username)
        return user
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

@app.post("/create_room/", status_code=201)
def create_room(room: RoomCreate):
    try:
        username = room.username
        user = User.get(username)
    except User.DoesNotExist:
        return {"message": "User not found", "status_code": 404}

    try:
        existing_room = Room.get(room.room_id)
        return {"message": "Room already exists", "status_code": 400}
    except Room.DoesNotExist:
        pass

    room_item = Room(
        room_id=room.room_id,
        room_name=room.room_name,
        users=[username]
    )
    room_item.save()

    user.rooms.append(room.room_id)
    user.save()
    return {"message": f"Room created successfully: {room.room_id} by {username}"}

@app.post("/join_room/", status_code=200)
async def join_room(join_room: UserRoomSchema):
    print(f"Received join request: {join_room.username}, {join_room.room_id}")

    try:
        user = User.get(join_room.username)
    except User.DoesNotExist:
        return {"message": "User does not exist", "status_code": 404}

    try:
        room = Room.get(join_room.room_id)
    except Room.DoesNotExist:
        return {"message": "Room does not exist", "status_code": 404}

    if join_room.room_id not in user.rooms:
        user.rooms.append(join_room.room_id)
        user.save()

    if join_room.username not in room.users:
        room.users.append(join_room.username)
        room.save()

    return {"message": f"{user.username} is joined in the room {room.room_name}"}


@app.post("/leave_room/", status_code=200)
async def user_leave_room(leave_room: UserRoomSchema):
    try:
        user = User.get(leave_room.username)
    except User.DoesNotExist:
        return {"message": "User does not exist", "status_code": 404}

    try:
        room = Room.get(leave_room.room_id)
    except Room.DoesNotExist:
        return {"message": "Room does not exist", "status_code": 404}

    if leave_room.room_id in user.rooms:
        user.rooms.remove(leave_room.room_id)
        user.save()

    if leave_room.username in room.users:
        room.users.remove(leave_room.username)
        room.save()

    return {"message": f"{user.username} has left the room {room.room_name}"}


@app.get("/rooms/{username}", response_model=list[RoomSchema])
async def get_user_rooms(username: str):
    print(f"Received rooms request: {username}")
    try:
        user = User.get(username)
        print(f"User rooms: {user.rooms}, user {user.username}")
    except User.DoesNotExist:
        return {"message": "No rooms available", "status_code": 404}

    rooms = []
    for room_id in user.rooms:
        try:
            room = Room.get(room_id)
            rooms.append(room)
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room does not exist")

    return rooms


@app.get("/room_details/{room_id}")
async def get_room_details(room_id: str):
    try:
        room = Room.get(room_id)
        # Scan all connections with matching room_id
        active_connections = list(Connection.scan(
            filter_condition=(Connection.room_id == room_id)
        ))
        active_users = sorted(set(conn.username for conn in active_connections))

        print(f"Active connections: {active_users}")

        return {
            "room_name": room.room_name,
            "active_users": active_users
        }
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")
    except Exception as e:
        print("Error in /room_details:", e, flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/messages/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str):
    print(f"Get messages request: {room_id}")
    messages = list(Message.scan(Message.room_id == room_id))
    for msg in messages:
        print(f"Message info: {msg.content}- {msg.timestamp}")
    return [MessageSchema(**{
        'message_id': msg.message_id,
        'content': msg.content,
        'username': msg.username,
        'room_id': msg.room_id,
        'timestamp': msg.timestamp
    }) for msg in messages]


@app.get("/ping")
async def ping():
    return {"message": "PONG"}


def handler(event, context):
    print("Lambda handler started")
    asgi_handler = Mangum(app)
    return asgi_handler(event, context)


print("Loaded Main Handler", flush=True)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)