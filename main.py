import hashlib
import uuid
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette import status

from models import User, Room, Base, Message
from database import engine, get_db
from schemas import UserCreate, RoomCreate, UserLogin, MessageSchema, RoomSchema, UserSchema, UserRoomSchema, \
    SendMessage, UsernameSchema, RoomIdSchema

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



@app.post("/create_room")
def create_room(room: RoomCreate, db: Session = Depends(get_db)):
    new_room = Room(
        room_id=room.room_id,
        room_name=room.room_name
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return {"message": f"Room created successfully: {new_room.room_id}"}

def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@app.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(user_info: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    if user:
        return {"message": "User already exists"}

    hashed_password = hash_password(user_info.password)
    new_user = User(
        username=user_info.username,
        password=hashed_password,
        fullname=user_info.fullname,
        email=user_info.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User created successfully: {new_user.username}"}

@app.post("/login/")
async def login(user_info: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    hashed_password = hash_password(user_info.password)
    actual_password = user.password
    if user:
        if actual_password == hashed_password:
            return {"message": f"User logged in successfully: {user.username}"}
        else:
            return {"message": "Wrong password"}

    return {"message": "User not found"}

@app.post("/user/", response_model=UserSchema)
async def get_user_profile(user_info: UsernameSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_info.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/send_message/")
async def send_message_in_room(message: MessageSchema, db: Session = Depends(get_db)):
    sender = db.query(User).filter(User.username == message.username).first()
    room = db.query(Room).filter(Room.room_id == message.room_id).first()
    sender_is_in_room = db.query(User).filter(User.rooms.any(room_id=message.room_id)).filter(User.username == message.username).first()
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
        timestamp=message.timestamp or datetime.now(datetime.UTC)
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return {"message": f"Message sent successfully: {new_message.message_id}"}


@app.post("/rooms/", response_model=list[RoomSchema])
async def get_user_rooms(user_details: UsernameSchema, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.username == user_details.username).all()
    user_rooms = []
    for user in users:
        for room in user.rooms:
            user_rooms.append(room.room_id)
    if len(user_rooms)==0:
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
    return {"message": f"{user.username} is joined in the room {room.room_name}"}

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


