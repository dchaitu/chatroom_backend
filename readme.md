Rest APIs

register_user -> Used to register a user
- path /register/
- Request
```json
{
    "username": "string",
    "password": "string",
    "fullname": "string",
    "email": "string",
    "recaptcha_token": "string"
}
```
- Response
```json
{
   "message": "User created successfully"
}

```
login -> Used to authenticate a user
- path /login/
- Request
```json
{
    "username": "string",
    "password": "string",
    "recaptcha_token": "string"
}
```
- Response
```json
{
   "message": "User logged in successfully: {user_info.username}",
        "status_code": 200,
        "access_token": "access_token",
        "token_type": "bearer"
}

```
get_user_profile -> Used to get a user info
- path /user/{username}
- Request
```json
{
  "username": "string"
}
```

- Response
```json
{
    "username": "string",
    "fullname": "string",
    "email": "string"
}
```

create_room -> Used to create a room for a user
- path /create_room/{username}
- Request
```json
{
  "room_id": "string",
  "room_name": "string"
}
```
- Response
```json
{
  "message": "Room created successfully: {room_id} by {username}"
}
```


join_room -> Used to join a room for a user which is already created
- path /join_room/
- Request

```json
{
  "username": "string",
  "room_id": "string"
}
```
- Response
```json
{
  "message": "{user.username} is joined in the room {room.room_name}", 
  "status_code": 200
}
```
user_leave_room -> Used to leave user from a room
- path /leave_room/
- Request
```json
{
  "username": "string",
  "room_id": "string"
}
```
- Response
```json
{
  "message": "{user.username} has left the room {room.room_name}",
  "status_code": 200
}
```

get_room_details -> Used to get room details (Will be saved in header of room)
- path /room_details/{room_id}
- Request
```json
{
  "room_id": "string"
}
```
- Response
```json
{
  "room_name": "string",
  "active_users": ["string"]
}
```
get_messages -> Used to get messages from a room
- path /messages/{room_id}
- Request
```json
{
  "room_id": "string"
}
```
- Response
```json
[
    {
        "message_id": "string",
        "content": "string",
        "username": "string",
        "room_id": "string",
        "timestamp": "string"
    }
]
```

Websocket APIs

$connect -> Used to connect to websocket

- Request username, room_id is taken from string parameters
- `PATH?username=${encodeURIComponent(username)}&room_id=${encodeURIComponent(roomId)}`

- Response
```json
{
  "message": "Connected",
  "statusCode": 200
}
```

$disconnect -> Used to disconnect from websocket

- Request is connection_id taken from string parameters

- Response
```json
{
  "message": "Disconnected",
  "statusCode": 200
}
```

sendmessage -> Used to send message to room members

- Request
```json
{
  "content": "string",
  "username": "string",
  "room_id": "string",
  "timestamp": "string"
}
```

- Response
```json
{
  "message": "Message sent",
  "statusCode": 200
}
```