import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter,status
from fastapi.params import Depends

from constants import get_current_user
from models import ReplyThread, Message
from schemas import ReplyThreadDTO, ReplyMessageDTO

router = APIRouter(prefix='/reply', tags=["Reply"])

@router.post("/create/", status_code=status.HTTP_201_CREATED, response_model=ReplyThreadDTO)
async def create_reply_to_message(reply_message: ReplyMessageDTO, username: str = Depends(get_current_user)):
    reply_thread = ReplyThread(
        thread_id=reply_message.message_id,  # or some grouping key thread_id not using need to remove it.
        reply_id=str(uuid.uuid4()),
        message_id=reply_message.message_id,
        content=reply_message.content,
        username=username,
    )
    reply_thread.save()
    print(f'reply_thread {reply_thread}')
    reply_thread_dto = ReplyThreadDTO(
        message_id=reply_thread.message_id,
        content=reply_thread.content,
        thread_id=reply_thread.thread_id,
        reply_id=reply_thread.reply_id,
        username=reply_thread.username,
        timestamp=reply_thread.timestamp,
    )


    return reply_thread_dto

@router.get('/{message_id}/count/')
async def get_message_reply_count(message_id: str):
    replies_for_message = list(ReplyThread.scan(filter_condition=(ReplyThread.message_id==message_id)))
    return {message_id: len(replies_for_message)}



@router.get('/show-replies-for/{message_id}/', response_model=List[ReplyThreadDTO])
async def show_replies_for_messages(message_id: str):
    replies_for_message = list(ReplyThread.scan(filter_condition=(ReplyThread.message_id==message_id)))
    print(f'replies_for_message {replies_for_message}')
    replies_for_message.sort(key=lambda r: r.timestamp)
    return replies_for_message


@router.get('/all-replies/', response_model=List[ReplyThreadDTO])
async def show_all_replies():
    all_replies = list(ReplyThread.scan())
    return all_replies