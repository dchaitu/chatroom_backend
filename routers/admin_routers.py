from typing import List

from fastapi import APIRouter, HTTPException, Depends

from constants import get_current_user
from models import Room, MembershipRequest, User, RoomMembership
from schemas import RoomSchema, MakeRoomAdmin, MembershipRequestSchema, UserActionDTO

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/create/", status_code=200, response_model=RoomSchema)
async def create_room_admin(room_admin: MakeRoomAdmin):
    try:
        room = Room.get(room_admin.room_id)
        room.admins.append(room_admin.username)
        room.save()

    except Room.DoesNotExist:
        raise HTTPException(status_code=404, detail="Room not found")

    return room


@router.get("/pending-requests/", response_model=List[MembershipRequestSchema])
async def get_pending_requests(request_type: str,username: str = Depends(get_current_user)):
    """Get all pending requests invite/join_request for rooms from other users to the admin"""
    # Get all rooms where user is admin
    pending_requests = list(MembershipRequest.scan(
        filter_condition=(MembershipRequest.status == "pending") & (MembershipRequest.request_type == request_type)
    ))
    room_ids = {req.room_id for req in pending_requests}
    print(f'room_ids: {room_ids}')
    #  Rooms for which user is admin
    rooms = {room.room_id: room for room in Room.batch_get(room_ids)}

    print(f"len of user_invitees_rooms: {len(pending_requests)}")
    filtered_pending_requests = [req for req in pending_requests
                             if username in rooms.get(req.room_id, Room()).admins
                             ]
    print(f"filtered_pending_requests: {filtered_pending_requests}")


    return filtered_pending_requests


# Endpoint for admin to accept/reject a user
@router.post("/request/{room_id}/respond/", status_code=200)
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
        print("Check if invite exists")
        member_request = MembershipRequest.get(room_id, user_invited)
    except MembershipRequest.DoesNotExist:
        raise HTTPException(status_code=404, detail="Invite not found")

    # Verify the responding user is an admin of the room

    if action == "accept":
        # Add user to room
        if user_invited not in room.users:
            room.users.append(user_invited)
            room.save()
            print(f"Room {room.room_name} added {user_invited} as member")
            # Update invite status
            user = User.get(user_invited)
            user.rooms.append(room_id)
            user.save()
            print(f"**User {user_invited} added to room {room_id}")
            RoomMembership(room_id=room_id, username=user_invited).save()


    member_request.status = "accepted" if action == "accept" else "rejected"
    member_request.save()

    return {
        "message": f"{action} Performed successfully on {user_invited} for room {room_id}"
    }