from typing import List

from fastapi import APIRouter, Depends

from constants import get_current_user
from schemas import RoomSchema, MakeRoomAdmin, MembershipRequestSchema, UserActionDTO
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/create/", status_code=200, response_model=RoomSchema)
async def create_room_admin(room_admin: MakeRoomAdmin, storage: StorageInterface = Depends(get_storage)):
    return await storage.create_room_admin(room_admin)


@router.get("/pending-requests/", response_model=List[MembershipRequestSchema])
async def get_pending_requests(request_type: str,username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    """Get all pending requests invite/join_request for rooms from other users to the admin"""
    return await storage.get_pending_requests(request_type,username)


# Endpoint for admin to accept/reject a user
@router.post("/request/{room_id}/respond/", status_code=200)
async def admin_respond_to_room_membership_request(
    room_id: str,
    user_action: UserActionDTO,
    current_user: str = Depends(get_current_user),
    storage: StorageInterface = Depends(get_storage)
):
    """Admin accepts or rejects a room joining request"""
    return await storage.admin_respond_to_room_membership_request(room_id, user_action, current_user)