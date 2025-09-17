from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, status, Depends

from constants import get_current_user
from models import UserReaction, Message
from schemas import ReactionDTO, UserReactionDTO

router = APIRouter(prefix="/reaction", tags=['Reaction'])


@router.post("/create/", status_code=status.HTTP_201_CREATED, response_model=UserReactionDTO)
def create_reaction_to_message(reaction: ReactionDTO, username: str = Depends(get_current_user)):
    try:
        user_reaction = UserReaction.get(reaction.message_id, username)
        if user_reaction.reaction_type == reaction.reaction_type:
            # Same reaction => toggle off/on
            user_reaction.delete()
        else:
            # Different reaction → update it
            user_reaction.reaction_type = reaction.reaction_type
            user_reaction.reacted_at = datetime.now(timezone.utc)
            user_reaction.save()
            return user_reaction

    except UserReaction.DoesNotExist:
        user_reaction = UserReaction(
            message_id=reaction.message_id,
            username=username,
            reaction_type=reaction.reaction_type,
            reacted_at=datetime.now(timezone.utc)
        )
        user_reaction.save()
        print("Saved:", user_reaction.serialize())
    return user_reaction



@router.get("/{room_id}/", response_model=List[UserReactionDTO])
def get_reactions_to_messages_in_room(room_id: str):
    messages_in_room = list(Message.scan(Message.room_id == room_id))
    message_ids = [message.message_id for message in messages_in_room]
    reactions = []
    for message in messages_in_room:
        reactions.extend(list(UserReaction.query(message.message_id)))

    return reactions

@router.get('/all-reactions/', response_model=List[UserReactionDTO])
def get_all_reactions():
    reactions = list(UserReaction.scan())
    return reactions