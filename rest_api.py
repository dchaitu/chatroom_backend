import shutil
import uuid
from typing import Optional

from starlette.staticfiles import StaticFiles

from constants import get_current_user

print("Starting", flush=True)
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import boto3


print("External Imports", flush=True)
from models import User, Room, Message, MembershipRequest, UserMessage
from schemas import MessageSchema, UserSchema, RoomSchema, MembershipRequestSchema, MessageInfoDTO
from routers.room_routers import router as room_router
from routers.user_routers import router as user_router
from routers.admin_routers import router as admin_router
from routers.reply_routers import router as reply_router
from routers.reaction_routers import router as reaction_router
print("Internal Imports", flush=True)
dynamodb = boto3.client('dynamodb')

print("List Dynamodb Tables", flush=True)
app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
origins = [
    "http://localhost",
    "http://localhost:3000",
    '*'
]
JWT_SECRET = os.environ.get('JWT_SECRET','p1beyVW)E>b{1gya{,I+yd]>DfN/\9#*')
secret_key = os.environ.get('RECAPTCHA_SECRET_KEY')

app.include_router(user_router)
app.include_router(room_router)
app.include_router(admin_router)
app.include_router(reply_router)
app.include_router(reaction_router)

# Consider this as static files storing uploaded files
app.mount("/uploads",StaticFiles(directory="uploads"),name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/all-rooms/", response_model=list[RoomSchema])
async def get_all_rooms():
    try:
        rooms = list(Room.scan())
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return rooms


@app.get("/all-users/", response_model=list[UserSchema])
def get_all_users():
    try:
        users = list(User.scan())
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="No users found")
    return users

@app.get("/all-requests/", response_model=list[MembershipRequestSchema])
def get_all_invitees_and_join_requests():
    try:
        membership_requests = list(MembershipRequest.scan())
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return membership_requests



@app.get("/messages/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str):
    print(f"Get messages request: {room_id}")
    messages = list(Message.scan(Message.room_id == room_id))
    for msg in messages:
        print(f"Message info: {msg.content}- {msg.timestamp}")
    messages_in_room = [
        MessageSchema(
            **{
                "message_id": msg.message_id,
                "content": msg.content,
                "username": msg.username,
                "room_id": msg.room_id,
                "timestamp": msg.timestamp,
                "file_url":msg.file_url
            }
        )
        for msg in messages
    ]
    messages_in_room = sorted(messages_in_room, key=lambda x:x.timestamp)
    return messages_in_room


@app.post("/send_message/", status_code=201, response_model=MessageSchema)
async def send_message(content: Optional[str] = Form(None),
                       room_id: str = Form(...),
                       file: Optional[UploadFile] = File(None),
                       username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    file_url = None
    if file:
        print("**********File Uploaded**********")
        ext = os.path.splitext(file.filename)[1]
        fname = f"{file.filename}{ext}"
        file_path = os.path.join(UPLOAD_DIR, fname)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"/{UPLOAD_DIR}/{fname}"

    # Save message
    message_item = Message(
        message_id=str(uuid.uuid4()),
        content=content,
        username=user.username,
        room_id=room_id,
        file_url=file_url
    )
    message_item.save()
    print("file_url ",file_url)
    # Save UserMessage Info
    user_message_item = UserMessage(
        message_id=message_item.message_id,
        username=user.username
    )
    user_message_item.save()

    return message_item

@app.get("/all-messages/", response_model=list[MessageSchema])
def get_all_messages():
    try:
        messages = list(Message.scan())
        messages = sorted(messages, key=lambda x: x.timestamp)
    except Message.DoesNotExist:
        raise HTTPException(status_code=404, detail="No messages found")

    return messages


@app.get("/message-info", response_model=list[MessageInfoDTO])
def get_message_last_seen_info(room_id: str):
    try:
        message_info_list = []
        room_messages = list(Message.scan(Message.room_id==room_id))
        for msg in room_messages:
            message_info = list(UserMessage.query(msg.message_id))
            print("message_info ", message_info)
            # return message_info
            # message_info = MessageInfoDTO(
            #     message_id=msg.message_id,
            #     username=msg.username,
            #     read_at=msg.read_at if hasattr(msg, "read_at") else msg.timestamp
            # )
            message_info_list.extend(message_info)

        print("message_info_list ",message_info_list)
        return message_info_list

    except UserMessage.DoesNotExist:
        raise HTTPException(status_code=404, detail="No messages found")


@app.post('/upload')
async def upload_file_with_message(file: UploadFile = File(...)):
    content = await file.read()
    print(content)


async def create_message_with_file(
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    username: str = Depends(get_current_user)  # if you have auth
):
    file_url = None
    if file:
        file_ext = os.path.splitext(file.filename)[1]
        print("File Details ",os.path.splitext(file.filename))
        saved_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_url = f"/{UPLOAD_DIR}/{saved_filename}"  # return path or S3 URL if uploading to cloud

    # Save the message in DB (DynamoDB, PynamoDB, etc.)
    message = {
        "message_id": str(uuid.uuid4()),
        "username": username,
        "content": content,
        "file_url": file_url,
    }

    print("Saved message:", message)
    return message




def handler(event, context):
    print("Lambda handler started")
    asgi_handler = Mangum(app)
    return asgi_handler(event, context)


print("Loaded Main Handler", flush=True)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rest_api:app", host="localhost", port=8080, reload=True)
