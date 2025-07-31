import hashlib

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import User, Room, Base, Message, Connection
from database import engine, get_db
from schemas import UserCreate, RoomCreate, UserLogin, MessageSchema, RoomSchema, UserSchema, UserRoomSchema

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

def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@app.post("/create_room")
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == room.username).first()
    print("Create room user",user, user.username)
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

@app.post("/register/", status_code=201)
async def register_user(user_info: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    if user:
        return {"message": "User already exists"}
    hashed_password = hash_password(user_info.password)
    new_user = User(username=user_info.username, password=hashed_password, fullname=user_info.fullname, email=user_info.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User created successfully: {new_user.username}"}

@app.post("/login/")
async def login(user_info: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    print(f"user {user}")
    hashed_password = hash_password(user_info.password)
    if user and user.password == hashed_password:
        return {"message": f"User logged in successfully: {user.username}", "status_code": 200}
    return {"message": "Invalid credentials", "status_code": 401}

@app.post("/user/{username}", response_model=UserSchema)
async def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/join_room/")
async def join_room(join_room: UserRoomSchema, db: Session = Depends(get_db)):
    print(f"Received join request: {join_room.username}, {join_room.room_id}")
    user = db.query(User).filter(User.username == join_room.username).first()
    room = db.query(Room).filter(Room.room_id == join_room.room_id).first()
    if not user:
        return {"message": "User does not exist", "status_code": 404}
    if not room:
        return {"message": "Room does not exist", "status_code": 404}
    user.rooms.append(room)
    db.commit()
    return {"message": f"{user.username} is joined in the room {room.room_name}", "status_code": 200}

@app.post("/leave_room/")
async def user_leave_room(leave_room: UserRoomSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == leave_room.username).first()
    room = db.query(Room).filter(Room.room_id == leave_room.room_id).first()
    if not user:
        return {"message": "User does not exist", "status_code": 404}
    if not room:
        return {"message": "Room does not exist", "status_code": 404}
    user.rooms.remove(room)
    db.commit()
    return {"message": f"{user.username} has left the room {room.room_name}", "status_code": 200}

@app.post("/rooms/{username}", response_model=list[RoomSchema])
async def get_user_rooms(username: str, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username == username).all()
    user_rooms = [room.room_id for user in users for room in user.rooms]
    if not user_rooms:
        return HTTPException(status_code=404, detail="No rooms available")
    return db.query(Room).filter(Room.room_id.in_(user_rooms)).all()

@app.post("/rooms/{username}/{room_id}/messages/", response_model=list[MessageSchema])
async def get_all_messages_in_room(room_id: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.room_id == room_id).all()
    return messages


@app.post("/room_details/{room_id}")
async def get_room_details(room_id:str, db: Session = Depends(get_db)):
    room_data = db.query(Room).filter(Room.room_id == room_id).first()
    if not room_data:
        raise HTTPException(status_code=404, detail="Room not found")

    # Fetch active users from the Connection table
    active_connections = db.query(Connection).filter(Connection.room_id == room_id).all()
    all_connections = db.query(Connection).all()
    print(f"Active connections: {[conn.username for conn in active_connections]}")
    print(f"All connections: {[conn.username for conn in all_connections]}")
    active_users = [conn.username for conn in active_connections]

    return {
        "room_name": room_data.room_name,
        "active_users": active_users
    }

@app.get("/messages/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.room_id == room_id).all()
    return messages

handler = Mangum(app)