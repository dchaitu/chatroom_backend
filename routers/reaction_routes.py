from typing import List, Optional

from fastapi import APIRouter, status, Depends

from constants import get_current_user
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface
from schemas import ReactionDTO, UserReactionDTO

router = APIRouter(prefix="/reaction", tags=['Reaction'])


@router.post("/create/", status_code=status.HTTP_201_CREATED, response_model=Optional[UserReactionDTO])
async def create_reaction_to_message(reaction: ReactionDTO, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.create_reaction_to_message(reaction, username)


@router.get("/{room_id}/", response_model=List[UserReactionDTO])
async def get_reactions_to_messages_in_room(room_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_reactions_to_messages_in_room(room_id)

@router.get('/all-reactions/', response_model=List[UserReactionDTO])
async def get_all_reactions(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_reactions()