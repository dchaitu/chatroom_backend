from typing import List

from fastapi import APIRouter,status
from fastapi.params import Depends

from constants import get_current_user
from schemas import ReplyThreadDTO, ReplyMessageDTO
from storages.storage_implementation import StorageImplementation
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface
router = APIRouter(prefix='/reply', tags=["Reply"])

@router.post("/create/", status_code=status.HTTP_201_CREATED, response_model=ReplyThreadDTO)
async def create_reply_to_message(reply_message: ReplyMessageDTO, username: str = Depends(get_current_user), storage: StorageInterface = Depends(get_storage)):
    return await storage.create_reply_to_message(reply_message, username)

@router.get('/{message_id}/count/')
async def get_message_reply_count(message_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_message_reply_count(message_id)

@router.get('/counts/')
async def get_all_message_reply_count(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_message_reply_count()



@router.get('/show-replies-for/{message_id}/', response_model=List[ReplyThreadDTO])
async def show_replies_for_messages(message_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.show_replies_for_messages(message_id)


@router.get('/all-replies/', response_model=List[ReplyThreadDTO])
async def show_all_replies(storage: StorageInterface = Depends(get_storage)):
    return await storage.show_all_replies()