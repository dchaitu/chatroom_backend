from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form

from constants import get_current_user
from dependencies import get_storage
from interactors.storage_interfaces.storage_interface import StorageInterface
from schemas import MessageSchema, MessageInfoDTO

router = APIRouter(prefix='/messages', tags=['Messages'])

@router.get("/{room_id}", response_model=list[MessageSchema])
async def get_messages(room_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_messages(room_id)


@router.post("/send/", status_code=201, response_model=MessageSchema)
async def send_message(content: Optional[str] = Form(None),
                       room_id: str = Form(...),
                       file: Optional[UploadFile] = File(None),
                       username: str = Depends(get_current_user),
                       storage: StorageInterface = Depends(get_storage)):

    return await storage.send_message(content, room_id, file, username)

@router.get("/all/", response_model=list[MessageSchema])
async def get_all_messages(storage: StorageInterface = Depends(get_storage)):
    return await storage.get_all_messages()


@router.get("/info/{room_id}", response_model=list[MessageInfoDTO])
async def get_message_last_seen_info(room_id: str, storage: StorageInterface = Depends(get_storage)):
    return await storage.get_message_last_seen_info(room_id)

