from fastapi import APIRouter

from dependencies import storage
from schemas import MembershipRequestSchema


router = APIRouter(prefix="/requests", tags=["Requests"])

@router.get("/all/", response_model=list[MembershipRequestSchema])
async def get_all_invitees_and_join_requests():
    return await storage.get_all_invitees_and_join_requests()