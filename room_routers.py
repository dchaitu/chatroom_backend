from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from constants import get_current_user
from models import User, Room, Connection,  MembershipRequest
from schemas import RoomCreate, RoomUpdate, RoomSchema, MembershipRequestSchema

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



@router.post("/join/", status_code=200)
async def join_room(room_id: str, username: str = Depends(get_current_user)):
    print(f"Received join request: {username}, {room_id}")

    try:
        user = User.get(username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    if room_id not in user.rooms:
        user.rooms.append(room_id)
        user.save()

    if username not in room.users:
        room.users.append(username)
        room.save()

    return {"message": f"{user.username} is joined in the room {room.room_name}"}


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

    rooms = []
    for room_id in user.rooms:
        try:
            room = Room.get(room_id)
            rooms.append(room)
        except Room.DoesNotExist:
            continue

    return rooms


@router.get("/all/", response_model=list[RoomSchema])
async def get_all_rooms():
    try:
        rooms = list(Room.scan())
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return rooms


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


@router.post("/{room_id}/invite/", status_code=201)
async def invite_user_to_room(
    room_id: str, invited_to: str, admin: str = Depends(get_current_user)
):
    """Admin invites a user to join a room."""
    try:
        room = Room.get(room_id)
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    if admin not in room.admins:
        raise HTTPException(
            status_code=403, detail="Only admins can invite users to this room."
        )

    # Check if user already in room
    if invited_to in room.users:
        raise HTTPException(status_code=400, detail="User already in room.")

    # Create invite

    invite = MembershipRequest(
        room_id=room_id,
        invited_by=admin,
        invited_to=invited_to,
        status="pending",
        request_type="invite"
    )
    invite.save()
    return {"message": f"Invite sent to {invited_to} for room {room_id}"}


@router.post("/{room_id}/request/", status_code=201)
def user_request_join_room(room_id: str, username: str = Depends(get_current_user)):
    """User requests admin to join a room."""
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
            raise HTTPException(status_code=400, detail="Already requested to join the room.")
    except:
        pass

    # Create join request
    membership_request = MembershipRequest(
        room_id=room_id,
        username=username,
        status="pending",
        request_type="join_request"
    )
    membership_request.save()
    return {"message": f"Join request sent for room {room_id} by {username} to approve"}


# Endpoint for admin to accept/reject a user
@router.post("/admin/invites/{room_id}/respond/", status_code=200)
async def respond_to_invite_membership_request(
        room_id: str,
        action: str,  # "accept" or "reject"
        username: str = Depends(get_current_user)
):
    """Admin accepts or rejects a room join request"""
    try:
        member_request = MembershipRequest.get(room_id,)
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Verify the responding user is an admin of the room
    try:
        room = Room.get(room_id)
        if username not in room.admins or username not in room.users:
            raise HTTPException(status_code=403, detail=f"{username} is not admin of the room")
    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    # Admin responding to user’s join request
    if member_request.request_type == "join_request":
        if username not in room.admins:
            raise HTTPException(status_code=403, detail="Only admins can approve join requests")

    # User responding to admin’s invite
    elif member_request.request_type == "invite":
        # if member_request. != username:
        #     raise HTTPException(status_code=403, detail="Only invited user can respond to this invite")
        pass
    if action == "accept":
        # Add user to room
        if username not in room.users:
            room.users.append(username)
            room.save()

        # Update invite status
        member_request.status = "accepted"
        member_request.save()

        # Optionally notify the user that they've been added to the room
        # (You'll need to implement this notification system)
        # notify_user(invite.invited_to, f"You've been added to room {room.room_name}")
        # room.users.append(invite.invited_to)
        # room.save()

        return {"message": f"Successfully added {username} to room {room.room_name}"}

    elif action == "reject":
        member_request.status = "rejected"
        member_request.save()
        return {"message": "Invite rejected"}

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'reject'")

@router.get("/admin/pending-invites/", response_model=List[dict])
async def get_pending_invites(username: str = Depends(get_current_user)):
    """Get all pending invites for rooms from other users to the admin"""
    # Get all rooms where user is admin
    user_invitees_rooms = MembershipRequest.username_status_index.query(
        username,
        MembershipRequest.status == "pending")
    print(f"user_invitees_rooms: {user_invitees_rooms}")
    pending_invites = []
    for invite in user_invitees_rooms:
        if invite.request_type == "invite":
            # only show invites, not join_requests
            pending_invites.append({
                "invite_id": invite.invite_id,
                "room_id": invite.room_id,
                "invited_by": invite.invited_by,
                "invited_to": invite.invited_to,
                "status": invite.status,
                "invited_at": str(invite.invited_at)
            })

    return pending_invites


@router.get("/admin/pending-join-requests/", response_model=List[dict])
async def get_pending_join_requests(username: str = Depends(get_current_user)):
    """Get all pending invites for rooms from other users to the admin"""
    # Get all rooms where user is admin
    user_invitees_rooms = MembershipRequest.username_status_index.query(
        username,
        MembershipRequest.status == "pending")
    print(f"user_invitees_rooms: {user_invitees_rooms}")
    pending_join_requests = []
    for invite in user_invitees_rooms:
        print(f"invite: {invite}")
        if invite.request_type == "join_request":
            # only show invites, not join_requests
            pending_join_requests.append({
                "room_id": invite.room_id,
                "username": username,
                "status": invite.status,
                "invited_at": invite.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

    return pending_join_requests


@router.get("/all_invitees-and-join-requests/", response_model=list[MembershipRequestSchema])
def get_all_invitees_and_join_requests():
    try:
        membership_requests = list(MembershipRequest.scan())
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="No rooms found")
    return membership_requests


# @router.get("/all_join_requests/", response_model=list[JoinRequestSchema])
# def get_all_join_requests():
#     try:
#         join_requests = list(JoinRequest.scan())
#     except JoinRequest.DoesNotExist:
#         raise HTTPException(status_code=404, detail="No join requests found")
#     return join_requests