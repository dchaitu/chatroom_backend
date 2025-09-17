from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from constants import get_current_user
from models import User, Room, Connection, MembershipRequest, RoomMembership, Message, UserMessage
from schemas import (
    RoomCreate,
    RoomUpdate,
    RoomSchema,
    MembershipRequestSchema,
    UserActionDTO, UserSchema, AddUserToRoomDTO, RoomMembershipDTO,
)

router = APIRouter(prefix="/room", tags=["Room"])


@router.post("/create/", status_code=201)
def create_room(room: RoomCreate, username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        existing_room = Room.get(room.room_id)
        raise HTTPException(status_code=400, detail="Room already exists")

    except Room.DoesNotExist:
        pass

    room_item = Room(
        room_id=room.room_id,
        room_name=room.room_name.strip(' '),
        users=[username],
        description=room.description,
        admins=[username],
    )
    room_item.save()

    user.rooms.append(room.room_id)
    user.save()
    return {"message": f"Room created successfully: {room.room_id} by {username}"}


@router.put("/create/", status_code=201)
def update_room(room: RoomUpdate, username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        existing_room = Room.get(room.room_id)
        if room.room_name:
            existing_room.room_name = room.room_name
        if room.description:
            existing_room.description = room.description
        existing_room.save()
        return {"message": f"Updated Room fields successfully: {room.room_name}"}

    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")





@router.post("/leave/", status_code=200)
async def user_leave_room(room_id: str, username: str = Depends(get_current_user)):
    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    if room_id in user.rooms:
        user.rooms.remove(room_id)
        user.save()

    if username in room.users:
        room.users.remove(username)
        room.save()

    return {"message": f"{user.username} has left the room {room.room_name}"}


@router.post("/{room_id}/mark-read")
async def mark_as_read(room_id: str, username: str = Depends(get_current_user)):
    """Update last_read_at when user opens a room"""
    membership = RoomMembership.get(room_id, username)
    membership.last_read_at = datetime.now(timezone.utc)
    membership.save()
    room_messages = list(Message.scan(Message.room_id==room_id))
    for msg in room_messages:
        try:
            UserMessage.get(msg.message_id, username)
        except UserMessage.DoesNotExist:
            user_message = UserMessage(
                message_id=msg.message_id,
                username=username,
                read_at=datetime.now(timezone.utc)
            )
            user_message.save()

    return {"message": "Marked as read"}

@router.get("/{room_id}/unread-count")
async def get_unread_count(room_id: str, username: str = Depends(get_current_user)):
    """Get count of unread messages for a user in a room"""
    membership = RoomMembership.get(room_id, username)
    last_read = membership.last_read_at

    unread_messages = Message.scan(
        (Message.room_id == room_id) & (Message.timestamp > last_read)
    )
    return {"count": len(list(unread_messages))}


@router.get("/user/", response_model=list[RoomSchema])
async def get_user_rooms(username: str = Depends(get_current_user)):
    print(f"Received rooms request: {username}")
    try:
        user = User.get(username)
        print(f"User rooms: {user.rooms}, user {user.username}")
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    room_ids = user.rooms
    rooms = []
    room_ids = list(set([room_id for room_id in room_ids]))
    for room_id in room_ids:
        try:
            room = Room.get(room_id)
            rooms.append(room)
        except Room.DoesNotExist:
            continue

    return rooms




@router.get("/available-rooms/", response_model=list[RoomSchema])
async def get_available_rooms(username: str = Depends(get_current_user)):
    """Rooms in which user is not a member"""
    user = User.get(username)
    current_rooms = list(Room.batch_get(user.rooms))
    print(f"current_rooms :- {[room.room_name for room in current_rooms]}")
    print(f"user.rooms :- {user.rooms}")
    all_rooms = list(Room.scan())
    available_rooms = [r for r in all_rooms if r.room_id not in user.rooms]
    print(f"available_rooms :- {[room.room_name for room in available_rooms]}")
    return available_rooms


@router.get("/room_details/{room_id}/", response_model=RoomSchema)
async def get_room_details(room_id: str):
    try:
        room = Room.get(room_id)
        return room
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")
    except Exception as e:
        print("Error in /room_details:", e, flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/invite/", status_code=201)
async def admin_add_user_to_room(
    add_user_to_room: AddUserToRoomDTO, current_user: str = Depends(get_current_user)
):
    """Admin invites a user to join a room."""
    room_id = add_user_to_room.room_id
    invited_user = add_user_to_room.added_user
    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    if current_user not in room.admins:
        raise HTTPException(
            status_code=403, detail="Only admins can invite users to this room."
        )

    # Check if user already in room
    if invited_user in room.users:
        raise HTTPException(status_code=400, detail="User already in room.")

    # Create invite

    membership_request = MembershipRequest(
        room_id=room_id,
        username=invited_user,
        status="pending",
        request_type="invite",
        created_by=current_user,
    )
    membership_request.save()
    return {"message": f"Invite sent to {invited_user} for room {room_id}"}


@router.post("/{room_id}/request/", status_code=201)
def user_request_join_room(room_id: str, username: str = Depends(get_current_user)):
    """User wants to join a room."""
    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check if already a member
    if username in room.users:
        raise HTTPException(status_code=400, detail="Already a member of the room.")

    # Check if already requested to join the room
    try:
        membership_request = MembershipRequest.get(room_id, username)
        if membership_request.status == "pending":
            raise HTTPException(
                status_code=400, detail="Already requested to join the room."
            )
    except:
        pass

    # Create join request
    membership_request = MembershipRequest(
        room_id=room_id,
        username=username,
        status="pending",
        request_type="join_request",
        created_by=username,
    )
    membership_request.save()
    return {"message": f"Join request sent for room {room_id} by {username} to approve"}




@router.post("/member/create/", response_model=RoomMembershipDTO)
async def create_room_membership(room_membership: RoomMembershipDTO):
    room_member = RoomMembership(room_id=room_membership.room_id,
                                 username=room_membership.username,
                                 last_read_at=room_membership.last_read_at,
                                 last_read_message_id=room_membership.last_read_message_id)
    room_member.save()
    return room_member








