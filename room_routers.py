from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from constants import get_current_user
from models import User, Room, Connection, MembershipRequest
from schemas import (
    RoomCreate,
    RoomUpdate,
    RoomSchema,
    MembershipRequestSchema,
    UserActionDTO, UserSchema, AddUserToRoomDTO,
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
        room_name=room.room_name,
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


@router.get("/all-rooms/", response_model=list[RoomSchema])
async def get_all_rooms():
    try:
        rooms = list(Room.scan())
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return rooms

@router.get("/available-rooms/", response_model=list[RoomSchema])
async def get_available_rooms(username: str = Depends(get_current_user)):

    user = User.get(username)
    if not user.rooms:  # if user has no rooms, return empty list
        return []
    current_rooms = list(Room.batch_get(user.rooms))
    print(f"current_rooms :- {[room.room_name for room in current_rooms]}")
    print(f"user.rooms :- {user.rooms}")
    all_rooms = list(Room.scan())
    available_rooms = [r for r in all_rooms if r.room_id not in user.rooms]
    print(f"available_rooms :- {[room.room_name for room in available_rooms]}")
    return available_rooms


@router.get("/room_details/{room_id}/")
async def get_room_details(room_id: str):
    try:
        room = Room.get(room_id)
        # Scan all connections with matching room_id
        active_connections = list(
            Connection.scan(filter_condition=(Connection.room_id == room_id))
        )
        # active_users = sorted(set(conn.username for conn in active_connections))
        room_members = room.users
        print(f"Active connections: {room_members}")

        return {
            "room_name": room.room_name,
            "room_members": room_members,
            "description": room.description,
        }
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


# Endpoint for admin to accept/reject a user
@router.post("/admin/request/{room_id}/respond/", status_code=200)
async def admin_respond_to_room_membership_request(
    room_id: str,
    user_action: UserActionDTO,
    current_user: str = Depends(get_current_user),
):
    """Admin accepts or rejects a room joining request"""
    try:
        room = Room.get(room_id)
        if current_user not in room.admins:
            raise HTTPException(status_code=403, detail="Only admins can respond to requests")
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    action = user_action.action
    user_invited = user_action.requested_user
    try:
        print("Received room membership request response:")
        member_request = MembershipRequest.get(room_id, user_invited)
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Verify the responding user is an admin of the room

    if action == "accept":
        # Add user to room
        if user_invited not in room.users:
            room.users.append(user_invited)
            room.save()
        print(f"User {user_invited} added to room {room_id}")

        # Update invite status
        try:
            user = User.get(user_invited)
            user.rooms.append(room_id)
            user.save()
            print(f"**User {user_invited} added to room {room_id}")
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

    # elif member_request.request_type == "join_request":
    if user_invited in room.admins and user_invited not in room.users:
        if action == "accept":
            room.users.append(user_invited)
            room.save()

    member_request.status = "accepted" if action == "accept" else "rejected"
    member_request.save()

    return {
        "message": f"{action} Performed successfully on {user_invited} for room {room_id}"
    }


@router.get("/admin/pending-invites/", response_model=List[MembershipRequestSchema])
async def get_pending_invites(username: str = Depends(get_current_user)):
    """Get all pending invites for rooms from other users to the admin"""
    # Get all rooms where user is admin
    pending_invitees = list(MembershipRequest.scan(
        filter_condition=(MembershipRequest.status == "pending") & (MembershipRequest.request_type == "invite")
    ))
    room_ids = {req.room_id for req in pending_invitees}
    print(f'room_ids: {room_ids}')
    #  Rooms for which user is admin
    rooms = {room.room_id: room for room in Room.batch_get(room_ids)}

    print(f"len of user_invitees_rooms: {len(pending_invitees)}")
    pending_invites = [req for req in pending_invitees
                             if username in rooms.get(req.room_id, Room()).admins
                             ]
    print(f"pending_invites: {pending_invites}")


    return pending_invites


@router.get("/admin/pending-join-requests/", response_model=List[MembershipRequestSchema])
async def get_pending_join_requests(username: str = Depends(get_current_user)):
    """Get all pending invites for rooms from other users to the admin"""
    # Get all rooms where user is admin
    pending_invitees = list(MembershipRequest.scan(
        filter_condition=(MembershipRequest.status == "pending") & (MembershipRequest.request_type == "join_request")
    ))
    room_ids = {req.room_id for req in pending_invitees}
    print(f'room_ids: {room_ids}')
    #  Rooms for which user is admin
    rooms = {room.room_id: room for room in Room.batch_get(room_ids)}

    print(f"len of user_invitees_rooms: {len(pending_invitees)}")
    pending_join_requests = [req for req in pending_invitees
                             if username in rooms.get(req.room_id, Room()).admins
                             ]


    return pending_join_requests


@router.get("/all-requests/", response_model=list[MembershipRequestSchema])
def get_all_invitees_and_join_requests():
    try:
        membership_requests = list(MembershipRequest.scan())
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return membership_requests

@router.get("/all-users/", response_model=list[UserSchema])
def get_all_users():
    try:
        users = list(User.scan())
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="No users found")
    return users
