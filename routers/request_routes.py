from fastapi import APIRouter

from schemas import MembershipRequestSchema
from storages.storage_implementation import StorageImplementation


router = APIRouter(prefix="/requests", tags=["Requests"])
storage = StorageImplementation()

@router.get("/all/", response_model=list[MembershipRequestSchema])
async def get_all_invitees_and_join_requests():
    return await storage.get_all_invitees_and_join_requests()