import abc
from typing import List, Optional

from fastapi import Form, Depends, UploadFile, File

from schemas import MakeRoomAdmin, UserActionDTO, ReactionDTO, UserReactionDTO, ReplyThreadDTO, \
    ReplyMessageDTO, RoomMembershipDTO, RoomSchema, AddUserToRoomDTO, RoomUpdate, RoomCreate, UpdateUserDTO, UserLogin, \
    UserCreate


class StorageInterface(abc.ABC):
    # admin_router
    @abc.abstractmethod
    async def create_room_admin(self,room_admin:MakeRoomAdmin):
        pass

    @abc.abstractmethod
    async def get_pending_requests(self, request_type: str, username: str):
        pass

    @abc.abstractmethod
    async def admin_respond_to_room_membership_request(
            self,
            room_id: str,
            user_action: UserActionDTO,
            current_user: str
    ):
        pass

    # reply_router
    @abc.abstractmethod
    async def create_reaction_to_message(self, reaction: ReactionDTO, username: str):
        pass


    @abc.abstractmethod
    async def get_reactions_to_messages_in_room(self, room_id: str) -> List[UserReactionDTO]:
        pass

    @abc.abstractmethod
    async def get_all_reactions(self):
        pass

    # reply_router
    @abc.abstractmethod
    async def create_reply_to_message(self, reply_message: ReplyMessageDTO, username: str):
        pass

    @abc.abstractmethod
    async def get_message_reply_count(self, message_id: str):
        pass

    @abc.abstractmethod
    async def get_all_message_reply_count(self):
        pass

    @abc.abstractmethod
    async def show_replies_for_messages(self, message_id: str)-> List[ReplyThreadDTO]:
        pass

    @abc.abstractmethod
    async def show_all_replies(self)->List[ReplyThreadDTO]:
        pass

    # room_router

    # room_router
    @abc.abstractmethod
    def create_room(self, room: RoomCreate, username: str):
        pass

    @abc.abstractmethod
    def update_room(self, room: RoomUpdate, username: str):
        pass

    @abc.abstractmethod
    async def user_leave_room(self, room_id: str, username: str):
        pass

    @abc.abstractmethod
    async def mark_as_read(self, room_id: str, username: str):
        """Update last_read_at when user opens a room"""
        pass

    @abc.abstractmethod
    async def get_unread_counts(self, room_ids: List[str], username: str):
        """Get count of unread messages for a user in each room"""
        pass

    @abc.abstractmethod
    async def get_user_rooms(self, username: str) -> list[RoomSchema]:
        pass
    @abc.abstractmethod
    async def get_available_rooms(self, username: str):
        """Rooms in which user is not a member"""
        pass
    @abc.abstractmethod
    async def get_room_details(self, room_id: str):
        pass
    @abc.abstractmethod
    async def admin_add_user_to_room(self,
                                     add_user_to_room: AddUserToRoomDTO, current_user: str
                                     ):
        """Admin invites a user to join a room."""
        pass

    @abc.abstractmethod
    def user_request_join_room(self, room_id: str, username: str):
        """User wants to join a room."""
        pass

    @abc.abstractmethod
    async def create_room_membership(self, room_membership: RoomMembershipDTO):
        pass

    # user_routers
    @abc.abstractmethod
    def register_user(self, user_info: UserCreate):
        pass

    @abc.abstractmethod
    def login(self, user_info: UserLogin):
        pass

    @abc.abstractmethod
    async def get_user_profile(self, username: str):
        pass

    @abc.abstractmethod
    async def update_user_profile(self, update_user: UpdateUserDTO, username: str):
        pass

    @abc.abstractmethod
    async def get_all_users(self):
        pass

    @abc.abstractmethod
    async def get_all_rooms(self):
        pass

    @abc.abstractmethod
    async def get_all_invitees_and_join_requests(self):
        pass


    @abc.abstractmethod
    async def get_messages(self, room_id: str):
        pass

    @abc.abstractmethod
    async def send_message(self, content: Optional[str] = Form(None),
                           room_id: str = Form(...),
                           file: Optional[UploadFile] = File(None),
                           username: str = Depends()):
        pass

    @abc.abstractmethod
    async def get_all_messages(self):
        pass

    @abc.abstractmethod
    async def get_message_last_seen_info(self, room_id: str):
        pass

