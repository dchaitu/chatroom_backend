import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, field_validator, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    fullname: str
    email: str
    avatar: str
    recaptcha_token: str
    pic_url: str

class RoomDTO(BaseModel):
    room_id: str
    room_name: Optional[str] = None
    description: Optional[str] = None

class RoomCreate(RoomDTO):
    pass

class RoomUpdate(BaseModel):
    pass

class MakeRoomAdmin(BaseModel):
    room_id: str
    username: str

class UserLogin(BaseModel):
    username: str
    password: str
    recaptcha_token: str

    model_config = {
        "json_schema_extra" : {
        "example": {
            "username": "chaitu",
            "password": "chaitu",
            "recaptcha_token": "string",
        }
    }
    }

class RoomSchema(RoomDTO):
    model_config = ConfigDict(from_attributes=True)
    users: List[str]
    admins: List[str]

    class Config:
        from_attributes = True
        orm_mode = True

class UserSchema(BaseModel):
    username: str
    fullname: str
    email: str
    avatar: str
    pic_url: Optional[str]

    class Config:
        from_attributes = True

class UpdateUserDTO(BaseModel):
    avatar: Optional[str] = None
    fullname: Optional[str] = None
    email: Optional[str] = None
    pic_url: Optional[str] = None

class UserRoomSchema(BaseModel):
    username: str
    room_id: str



class MessageSchema(BaseModel):
    message_id: str
    content: str
    username: str
    room_id: str
    timestamp: Optional[datetime]
    file_url: Optional[str] = None


    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    username: str
    room_id: str
    file_url: Optional[str] = None

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

class AddUserToRoomDTO(BaseModel):
    room_id: str
    added_user: str

class RoomMembershipDTO(BaseModel):
    room_id: str
    username: str
    last_read_at: Optional[datetime]
    last_read_message_id: Optional[str]


class MessageInfoDTO(BaseModel):
    message_id: str
    username: str
    read_at: Optional[datetime]

class ReplyMessageDTO(BaseModel):
    message_id: str
    content: str


class ReplyThreadDTO(ReplyMessageDTO):
    thread_id: str
    reply_id: str
    username: str
    timestamp: Optional[datetime]

emoji_pattern = re.compile(
    "[" 
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "]+",
    flags=re.UNICODE
)

class ReactionDTO(BaseModel):
    message_id: str
    reaction_type: str

    # @field_validator("reaction_type")
    # def must_be_emoji(cls, v):
    #     if not emoji_pattern.match(v):
    #         raise ValueError("reaction_type must be an emoji")
    #     return v

class UserReactionDTO(ReactionDTO):
    username: str
    reacted_at: Optional[datetime]


