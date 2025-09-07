from datetime import datetime
from typing import Optional, List

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
    description: str

class RoomUpdate(BaseModel):
    room_id: str
    room_name: Optional[str] = None
    description: Optional[str] = None

class MakeRoomAdmin(BaseModel):
    room_id: str
    username: str

class UserLogin(BaseModel):
    username: str
    password: str
    recaptcha_token: str


class RoomSchema(BaseModel):
    room_id: str
    room_name: str
    description: str
    users: List[str]
    admins: List[str]

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
    content: str
    room_id: str

class MembershipRequestSchema(BaseModel):
    room_id: str
    username: str
    request_type: str
    status: str
    created_by: str
    created_at: Optional[datetime]

class UserActionDTO(BaseModel):
    requested_user: str
    action: str
