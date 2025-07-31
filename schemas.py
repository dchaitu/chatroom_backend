from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    fullname: str
    email: str
    recaptcha_token: str

class RoomCreate(BaseModel):
    room_id: str
    room_name: str
    username: str


class UserLogin(BaseModel):
    username: str
    password: str
    recaptcha_token: str


class RoomSchema(BaseModel):
    room_id: str
    room_name: str

    class Config:
        from_attributes = True

class UserSchema(BaseModel):
    username: str
    fullname: str
    email: str

    class Config:
        from_attributes = True

class UserRoomSchema(BaseModel):
    username: str
    room_id: str



class MessageSchema(BaseModel):
    content: str
    username: str
    room_id: str
    timestamp: Optional[datetime]


    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    username: str
    room_id: str

class SendMessage(BaseModel):
    message_id: str
    content: str
    username: str
    timestamp: datetime


