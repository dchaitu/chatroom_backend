import hashlib

from boto3 import Session
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from datetime import datetime, timedelta
import jwt

from constants import JWT_SECRET
from models import User, Room, Message, Connection
from database import get_db
from schemas import UserCreate, RoomCreate, UserLogin, MessageSchema, RoomSchema, UserSchema, UserRoomSchema

app = FastAPI()

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

def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_access_token(username: str, expires_delta: timedelta = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

@app.post("/create_room")
def create_room(room: RoomCreate, db = Depends(get_db)):
    User = db['users']
    Room = db['rooms']
    user = User.get(room.username)
    if not user:
        return {"message": "User not found", "status_code": 404}
    if Room.get(room.room_id):
        return {"message": "Room already exists", "status_code": 400}
    room_item = Room(
        room_id=room.room_id,
        room_name=room.room_name,
        users=[room.username]
    )
    room_item.save()
    user.rooms.append(room.room_id)
    user.save()
    return {"message": f"Room created successfully: {room.room_id}"}

@app.post("/register/", status_code=201)
async def register_user(user_info: UserCreate, db=Depends(get_db)):
    User = db['users']
    if User.get(user_info.username):
        return {"message": "User already exists"}
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

@app.post("/login/")
async def login(user_info: UserLogin, db = Depends(get_db)):
    User = db['users']
    user = User.get(user_info.username)
    if not user or user.password != hash_password(user_info.password):
        return {"message": "Invalid credentials", "status_code": 401}
    access_token = create_access_token(user_info.username)
    return {
        "message": f"User logged in successfully: {user_info.username}",
        "status_code": 200,
        "access": access_token,
        "refresh": create_access_token(user_info.username, timedelta(days=7))
    }

@app.post("/user/{username}", response_model=UserSchema)
async def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = User.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/join_room/")
async def join_room(join_room: UserRoomSchema, db = Depends(get_db)):
    print(f"Received join request: {join_room.username}, {join_room.room_id}")
    User = db['users']
    Room = db['rooms']
    user = User.get(join_room.username)
    room = Room.get(join_room.room_id)
    if not user:
        return {"message": "User does not exist", "status_code": 404}
    if not room:
        return {"message": "Room does not exist", "status_code": 404}
    if join_room.room_id not in user.rooms:
        user.rooms.append(join_room.room_id)
        user.save()
    if join_room.username not in room.users:
        room.users.append(join_room.username)
        room.save()
    return {"message": f"{user.username} is joined in the room {room.room_name}", "status_code": 200}

@app.post("/leave_room/")
async def user_leave_room(leave_room: UserRoomSchema, db: Session = Depends(get_db)):
    user = User.get(leave_room.username)
    room = Room.get(leave_room.room_id)
    if not user:
        return {"message": "User does not exist", "status_code": 404}
    if not room:
        return {"message": "Room does not exist", "status_code": 404}
    if leave_room.room_id in user.rooms:
        user.rooms.remove(leave_room.room_id)
        user.save()
    if leave_room.username in room.users:
        room.users.remove(leave_room.username)
        room.save()

    return {"message": f"{user.username} has left the room {room.room_name}", "status_code": 200}

@app.get("/rooms/{username}", response_model=list[RoomSchema])
async def get_user_rooms(username: str, db = Depends(get_db)):
    User = db['users']
    Room = db['rooms']
    user = User.get(username)
    if not user:
        return {"message": "No rooms available", "status_code": 404}
    rooms = [Room.get(room_id) for room_id in user.rooms if Room.get(room_id)]
    return [room for room in rooms if room]

@app.get("/rooms/{username}/{room_id}/messages/", response_model=list[MessageSchema])
async def get_all_messages_in_room(room_id: str, db: Session = Depends(get_db)):
    Message = db['messages']
    messages = Message.query(room_id)
    return [message.attribute_values for message in messages]

@app.get("/room_details/{room_id}")
async def get_room_details(room_id:str, db: Session = Depends(get_db)):
    Room = db['rooms']
    try:
        # 1. Get the room
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

        # 2. Scan all connections with matching room_id (can optimize with GSI)
    active_connections = list(Connection.scan(Connection.room_id == room_id))
    # 3. Extract active usernames
    active_users = [conn.username for conn in active_connections]

    print(f"Active connections: {active_users}")

    return {
        "room_name": room.room_name,
        "active_users": active_users
    }

@app.get("/messages/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str, db: Session = Depends(get_db)):
    Message = db['messages']
    messages = Message.query(room_id)
    return [MessageSchema(**{
        'message_id': msg.message_id,
        'content': msg.content,
        'username': msg.username,
        'room_id': msg.room_id,
        'timestamp': msg.timestamp.isoformat()
    }) for msg in messages]

handler = Mangum(app)