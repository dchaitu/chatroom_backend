import abc
from typing import List, Optional, Dict, Any

from fastapi import Form, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from schemas import MakeRoomAdmin, UserActionDTO, ReactionDTO, UserReactionDTO, ReplyThreadDTO, \
    ReplyMessageDTO, RoomMembershipDTO, RoomSchema, AddUserToRoomDTO, RoomUpdate, RoomCreate, UpdateUserDTO, UserLogin, \
    UserCreate, MessageInfoDTO, MessageSchema, UserSchema, UserReactionDTO
from database import get_db


class StorageInterface(abc.ABC):
    # admin_router
    @abc.abstractmethod
    async def create_room_admin(self, room_admin: MakeRoomAdmin, db: Session = Depends(get_db)) -> RoomSchema:
        pass

    @abc.abstractmethod
    async def get_pending_requests(self, request_type: str, username: str, db: Session = Depends(get_db)) -> List[Any]:
        pass

    @abc.abstractmethod
    async def admin_respond_to_room_membership_request(
            self,
            room_id: str,
            user_action: UserActionDTO,
            current_user: str,
            db: Session = Depends(get_db)
    ) -> Dict[str, str]:
        pass

    # reply_router
    @abc.abstractmethod
    async def create_reaction_to_message(self, reaction: ReactionDTO, username: str, db: Session = Depends(get_db)) -> UserReactionDTO:
        pass


    @abc.abstractmethod
    async def get_reactions_to_messages_in_room(self, room_id: str, db: Session = Depends(get_db)) -> List[UserReactionDTO]:
        pass

    @abc.abstractmethod
    async def get_all_reactions(self, db: Session = Depends(get_db)) -> List[UserReactionDTO]:
        pass

    # reply_router
    @abc.abstractmethod
    async def create_reply_to_message(self, reply_message: ReplyMessageDTO, username: str, db: Session = Depends(get_db)) -> ReplyThreadDTO:
        pass

    @abc.abstractmethod
    async def get_message_reply_count(self, message_id: str, db: Session = Depends(get_db)) -> Dict[str, int]:
        pass

    @abc.abstractmethod
    async def get_all_message_reply_count(self, db: Session = Depends(get_db)) -> Dict[str, int]:
        pass

    @abc.abstractmethod
    async def show_replies_for_messages(self, message_id: str, db: Session = Depends(get_db)) -> List[ReplyThreadDTO]:
        pass

    @abc.abstractmethod
    async def show_all_replies(self, db: Session = Depends(get_db)) -> List[ReplyThreadDTO]:
        pass


    # room_router
    @abc.abstractmethod
    async def create_room(self, room: RoomCreate, username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
        pass

    @abc.abstractmethod
    async def update_room(self, room: RoomUpdate, username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
        pass

    @abc.abstractmethod
    async def user_leave_room(self, room_id: str, username: str, db: Session = Depends(get_db)) -> None:
        pass

    @abc.abstractmethod
    async def mark_as_read(self, room_id: str, username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
        """Update last_read_at when user opens a room"""
        pass

    @abc.abstractmethod
    async def get_unread_counts(self, room_ids: List[str], username: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
        """Get count of unread messages for a user in each room"""
        pass

    @abc.abstractmethod
    async def get_user_rooms(self, username: str, db: Session = Depends(get_db)) -> List[RoomSchema]:
        pass
    @abc.abstractmethod
    async def get_available_rooms(self, username: str, db: Session = Depends(get_db)) -> List[RoomSchema]:
        """Rooms in which user is not a member"""
        pass
    @abc.abstractmethod
    async def get_room_details(self, room_id: str, db: Session = Depends(get_db)) -> RoomSchema:
        pass

    @abc.abstractmethod
    async def get_room_admins(self, room_id: str, db: Session = Depends(get_db)) -> List[str]:
        pass

    @abc.abstractmethod
    async def admin_add_user_to_room(
            self,
            add_user_to_room: AddUserToRoomDTO, 
            current_user: str,
            db: Session = Depends(get_db)
    ) -> Dict[str, str]:
        """Admin invites a user to join a room."""
        pass

    @abc.abstractmethod
    async def user_request_join_room(self, room_id: str, username: str, db: Session = Depends(get_db)) -> Dict[str, str]:
        """User wants to join a room."""
        pass

    @abc.abstractmethod
    async def create_room_membership(self, room_membership: RoomMembershipDTO, db: Session = Depends(get_db)) -> RoomMembershipDTO:
        pass

    # user_routers
    @abc.abstractmethod
    async def register_user(self, user_info: UserCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def login(self, user_info: UserLogin, db: Session = Depends(get_db)) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def get_user_profile(self, username: str, db: Session = Depends(get_db)) -> UserSchema:
        pass

    @abc.abstractmethod
    async def update_user_profile(self, update_user: UpdateUserDTO, username: str, db: Session = Depends(get_db)) -> UserSchema:
        pass

    @abc.abstractmethod
    async def get_all_users(self, db: Session = Depends(get_db)) -> List[UserSchema]:
        pass

    @abc.abstractmethod
    async def get_all_rooms(self, db: Session = Depends(get_db)) -> List[RoomSchema]:
        pass

    @abc.abstractmethod
    async def get_all_invitees_and_join_requests(self, db: Session = Depends(get_db)) -> List[Any]:
        pass


    @abc.abstractmethod
    async def get_messages(self, room_id: str, db: Session = Depends(get_db)) -> List[MessageSchema]:
        pass

    @abc.abstractmethod
    async def send_message(self, 
                          content: Optional[str] = Form(None),
                          room_id: str = Form(...),
                          file: Optional[UploadFile] = File(None),
                          username: str = Depends(),
                          db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def get_all_messages(self, db: Session = Depends(get_db)) -> List[MessageSchema]:
        pass

    @abc.abstractmethod
    async def get_message_last_seen_info(self, room_id: str, db: Session = Depends(get_db)) -> List[MessageInfoDTO]:
        pass

