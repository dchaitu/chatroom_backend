from fastapi import APIRouter, Depends, status
from typing import List, Dict
router = APIRouter(prefix="/room", tags=["Room"])

from constants import get_current_user
from schemas import (
    RoomCreate, 
    RoomUpdate, 
    RoomSchema,
    RoomMembershipDTO,
    AddUserToRoomDTO
)
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface

@router.post("/create/", status_code=status.HTTP_201_CREATED)
async def create_room(room: RoomCreate, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.create_room(room, username)



@router.put("/update/", status_code=status.HTTP_200_OK)
async def update_room(room: RoomUpdate, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.update_room(room, username)

@router.post("/leave/", status_code=status.HTTP_200_OK)
async def user_leave_room(room_id: str, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.user_leave_room(room_id, username)

@router.post("/{room_id}/mark-read", status_code=status.HTTP_200_OK)
async def mark_as_read(room_id: str, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.mark_as_read(room_id, username)

@router.post("/unread-count")
async def get_unread_counts(room_ids: List[str], username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.get_unread_counts(room_ids, username)

@router.get("/user/", response_model=List[RoomSchema])
async def get_user_rooms(username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.get_user_rooms(username)

@router.get("/available-rooms/", response_model=List[RoomSchema])
async def get_available_rooms(username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.get_available_rooms(username)

@router.get("/{room_id}", response_model=RoomSchema)
async def get_room_details(room_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_room_details(room_id)

@router.get("/{room_id}/admins", response_model=List[str])
async def get_room_admins(room_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_room_admins(room_id)

@router.post("/admin/add-user/", status_code=status.HTTP_200_OK)
async def admin_add_user_to_room(
    add_user_to_room: AddUserToRoomDTO, 
    current_user: str = Depends(get_current_user),
    storage: StorageInterface = Depends(get_storage)
):
    return await storage.admin_add_user_to_room(add_user_to_room, current_user)

@router.post("/{room_id}/join/", status_code=status.HTTP_200_OK)
async def user_request_join_room(room_id: str, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.user_request_join_room(room_id, username)

@router.post("/membership/", status_code=status.HTTP_201_CREATED)
async def create_room_membership(room_membership: RoomMembershipDTO, storage: StorageInterface = Depends(get_storage)):
    return await storage.create_room_membership(room_membership)

@router.post("/invite/", status_code=status.HTTP_201_CREATED)
async def admin_add_user_to_room(
    add_user_to_room: AddUserToRoomDTO, current_user: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)
):
    """Admin invites a user to join a room."""
    return await storage.admin_add_user_to_room(add_user_to_room, current_user)


@router.post("/{room_id}/request/", status_code=status.HTTP_201_CREATED)
async def user_request_join_room(room_id: str, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    """User wants to join a room."""
    # Create join request

    return await storage.user_request_join_room(room_id, username)

@router.get("/all/", response_model=list[RoomSchema])
async def get_all_rooms(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_rooms()