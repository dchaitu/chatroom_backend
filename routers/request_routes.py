from fastapi import APIRouter, Depends

from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface
from schemas import MembershipRequestSchema


router = APIRouter(prefix="/requests", tags=["Requests"])

@router.get("/all/", response_model=list[MembershipRequestSchema])
async def get_all_invitees_and_join_requests(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_invitees_and_join_requests()