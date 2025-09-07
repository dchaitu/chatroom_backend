import uuid
from constants import hash_password, create_access_token, get_current_user

print("Starting", flush=True)
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import boto3


print("External Imports", flush=True)
from models import User, Room, Message, Connection
from schemas import MessageSchema, RoomSchema, UserSchema, \
    SendMessage, RoomUpdate, MakeRoomAdmin
from room_routers import router as room_router
from user_routers import router as user_router
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

app.include_router(user_router)
app.include_router(room_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.post("/make_admin/", status_code=200, response_model=RoomSchema)
async def create_room_admin(room_admin: MakeRoomAdmin):
    try:
        room = Room.get(room_admin.room_id)
        room.admins.append(room_admin.username)
        room.save()

    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    return room




@app.get("/messages/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str):
    print(f"Get messages request: {room_id}")
    messages = list(Message.scan(Message.room_id == room_id))
    for msg in messages:
        print(f"Message info: {msg.content}- {msg.timestamp}")
    return [
        MessageSchema(
            **{
                "message_id": msg.message_id,
                "content": msg.content,
                "username": msg.username,
                "room_id": msg.room_id,
                "timestamp": msg.timestamp,
            }
        )
        for msg in messages
    ]


@app.post("/send_message/", status_code=201)
async def send_message(message: SendMessage, username: str = Depends(get_current_user)):
    print(f"Received send_message request: {message}")
    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        room = Room.get(message.room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    # Save message
    message_item = Message(
        message_id=str(uuid.uuid4()),
        content=message.content,
        username=user.username,
        room_id=message.room_id
    )
    message_item.save()

    return {
        "message": "Message sent successfully by {} in {}".format(
            username, room.room_name
        )
    }











def handler(event, context):
    print("Lambda handler started")
    asgi_handler = Mangum(app)
    return asgi_handler(event, context)


print("Loaded Main Handler", flush=True)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rest_api:app", host="localhost", port=8080, reload=True)
