import os
import shutil
import uuid
from collections import defaultdict
from datetime import timezone, datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status, Form, UploadFile, File, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from constants import hash_password, create_access_token, UPLOAD_DIR
from interactors.storage_interfaces.storage_interface import StorageInterface
from models.rds_models import User, engine, RoomMembership, Room, MembershipRequest, UserReaction, ReplyThread, Message, UserMessage
from schemas import MakeRoomAdmin, RoomCreate, RoomUpdate, RoomSchema, AddUserToRoomDTO, RoomMembershipDTO, UserCreate, \
    UserLogin, UserSchema, UpdateUserDTO, MessageSchema, MembershipRequestSchema, UserActionDTO, ReactionDTO, \
    ReplyMessageDTO


class RDSStorageImplementation(StorageInterface):
    async def create_room_admin(self, room_admin: MakeRoomAdmin):
        room = select(Room).where(Room.room_id == room_admin.room_id)

        with Session(engine) as session:
            room = session.execute(room).scalar_one_or_none()
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")

            for membership in room.room_memberships:
                if membership.username == room_admin.username:
                    membership.is_admin = True
                    session.commit()
        return {"message": f"User {room_admin.username} is now an admin of room {room.room_id}"}



    async def get_pending_requests(self, request_type: str, username: str):
        statement = select(MembershipRequest).where(
            (MembershipRequest.request_type == request_type) & (MembershipRequest.status == "pending")
            & (MembershipRequest.username == username)
        )
        with Session(engine) as session:
            pending_requests = session.execute(statement).scalars().all()
            # room_ids = [req.room_id for req in pending_requests]
        return pending_requests

    async def admin_respond_to_room_membership_request(
            self,
            room_id: str,
            user_action: UserActionDTO,
            current_user: str
    ):
        with Session(engine) as session:
            try:
                action = user_action.action
                user_invited = user_action.requested_user
                membership_request = select(MembershipRequest).where(
                    (MembershipRequest.room_id == room_id) & (MembershipRequest.username == user_invited)
                )
            except Exception:
                raise HTTPException(status_code=404, detail="Membership request not found")

            membership_request = session.execute(membership_request).scalar_one_or_none()
            if membership_request is None:
                raise HTTPException(status_code=404, detail="Membership request not found")

            if action == "accept":
                membership_request.status = "accepted"
            elif action == "reject":
                membership_request.status = "rejected"
            session.commit()
        return {"message": f"Membership request {action} for user {user_invited} in room {room_id}"}


    async def create_reaction_to_message(self, reaction: ReactionDTO, username: str):
        with Session(engine) as session:
            try:
                user_reaction = select(UserReaction).where(
                    (UserReaction.message_id == reaction.message_id) & (UserReaction.username == username)
                )
                user_reaction = session.execute(user_reaction).scalar_one_or_none()
                if user_reaction.reaction_type == reaction.reaction_type:
                    session.delete(user_reaction)
                else:
                    user_reaction.reaction_type = reaction.reaction_type
                    user_reaction.reacted_at = datetime.now(timezone.utc)
                    session.add(user_reaction)
                session.commit()
            except Exception:
                raise HTTPException(status_code=404, detail="User reaction not found")

        return user_reaction

    #



    async def get_all_reactions(self):
        statement = select(UserReaction)
        reactions = []
        with Session(engine) as session:
            reactions = session.execute(statement).scalars().all()
        return reactions

    async def create_reply_to_message(self, reply_message: ReplyMessageDTO, username: str):
        with Session(engine) as session:
            reply_thread = ReplyThread(
                message_id=reply_message.message_id,
                reply_message=reply_message.reply_message,
                username=username,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(reply_thread)
            session.commit()
            reply_thread_dto = ReplyMessageDTO.model_validate(reply_thread)
        return reply_thread_dto


    async def get_message_reply_count(self, message_id: str):
        statement = select(ReplyThread).where(ReplyThread.message_id == message_id)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
        return {message_id: len(replies_for_message)}

    async def get_all_message_reply_count(self):
        statement = select(ReplyThread)
        message_wise_replies_count = defaultdict(int)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
            for reply in replies_for_message:
                message_wise_replies_count[reply.message_id] += 1

        return message_wise_replies_count

    async def show_replies_for_messages(self, message_id: str):
        statement = select(ReplyThread).where(ReplyThread.message_id == message_id)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
            replies_for_message.sort(key=lambda r: r.timestamp)

        return replies_for_message


    async def show_all_replies(self):
        statement = select(ReplyThread)
        with Session(engine) as session:
            replies = session.execute(statement).scalars().all()
            # replies.sort(key=lambda r: r.timestamp)
        return replies

    async def create_room(self, room: RoomCreate, username: str):
        with Session(engine) as session:
            try:
                user = session.get(User, username)
                check_room = session.get(Room, room.room_id)
            except Exception:
                raise HTTPException(status_code=404, detail="User/Room not found")

            room = Room(
                room_id=room.room_id,
                room_name=room.room_name.strip(' '),
                description=room.description,
                users=[user],
            )
            session.add(room)
            session.commit()

        return {"message": f"Room created successfully: {room.room_id} by {username}"}


    async def update_room(self, room: RoomUpdate, username: str):
        with Session(engine) as session:
            existing_room = session.get(Room, room.room_id)
            if existing_room is None:
                raise HTTPException(status_code=404, detail="Room not found")
            if existing_room.room_name:
                existing_room.room_name = room.room_name
            if existing_room.description:
                existing_room.description = room.description
            # existing_room.save()
            session.commit()
        return {"message": f"Updated Room fields successfully: {room.room_name}"}


    async def user_leave_room(self, room_id: str, username: str):
        with Session(engine) as session:
            user = session.get(User, username)
            room = session.get(Room, room_id)
            if room_id in user.rooms:
                user.rooms.remove(room)
                session.commit()


    async def mark_as_read(self, room_id: str, username: str):
        with Session(engine) as session:
            statement = select(RoomMembership).where((RoomMembership.room_id == room_id) & (RoomMembership.username== username))
            membership = session.execute(statement).scalar_one_or_none()
            membership.last_read_at = datetime.now(timezone.utc)
            session.commit()
            room_messages = session.execute(select(Message).where(Message.room_id == room_id)).scalars().all()
            for msg in room_messages:
                try:
                    user_message = session.get(UserMessage, (msg.message_id, username))
                except Exception:
                    user_message = UserMessage(
                        message_id=msg.message_id,
                        username=username,
                        read_at=datetime.now(timezone.utc)
                    )
                    session.add(user_message)
                    session.commit()

            return {"message": "Marked as read"}


    async def get_unread_counts(self, room_ids: List[str], username: str):
        # pass
        membership = select(RoomMembership).where((RoomMembership.username== username))

        filter_membership = select(membership).where(membership.room_id.in_(room_ids))
        with Session(engine) as session:
            filter_memberships = session.execute(filter_membership).scalars().all()
            unread_counts = []
            for membership in filter_memberships:
                unread_counts.append({"room_id": membership.room_id, "count": len(membership.unread_messages)})

        return unread_counts

    async def get_user_rooms(self, username: str) -> List[RoomSchema]:
        statement = select(User).where(User.username == username)
        with Session(engine) as session:
            user = session.execute(statement).scalar_one_or_none()
            rooms = user.rooms
            room_dtos = [RoomSchema.model_validate(room) for room in rooms]
        return room_dtos

    async def get_available_rooms(self, username: str):
        with Session(engine) as session:
            user_rooms = session.get(User, username).rooms
            all_rooms = session.execute(select(Room)).scalars().all()
            available_rooms = [room for room in all_rooms if room.room_id not in user_rooms]
            room_dtos = [RoomSchema.model_validate(room) for room in available_rooms]
        return room_dtos

    async def get_room_details(self, room_id: str):
        with Session(engine) as session:
            room = session.get(Room, room_id)
            room_dto = RoomSchema.model_validate(room)

        return room_dto

    async def admin_add_user_to_room(self,
                                     add_user_to_room: AddUserToRoomDTO, current_user: str
                                     ):
        with Session(engine) as session:
            current_room_id = add_user_to_room.room_id
            room = session.get(Room, current_room_id)
            room_membership = select(RoomMembership).where(
                (RoomMembership.room_id == current_room_id) &
                (RoomMembership.username == current_user) &
                (RoomMembership.is_admin == True)
            )
            room_membership_result = session.execute(room_membership).scalar_one_or_none()
            if room_membership_result is None:
                raise HTTPException(status_code=403, detail="Only admins can invite users to this room.")

            invited_user = session.get(User, add_user_to_room.added_user)
            if invited_user not in room.users:
                raise HTTPException(status_code=400, detail="User already in room.")

            membership_request = MembershipRequest(
                room_id=current_room_id,
                username=invited_user,
                status="pending",
                request_type="invite",
                created_by=current_user,
            )
            session.add(membership_request)
            session.commit()

        return {"message": f"Invite sent to {invited_user} for room {current_room_id}"}

    async def user_request_join_room(self, room_id: str, username: str):
        with Session(engine) as session:
            membership_request = select(MembershipRequest).where(
                (MembershipRequest.room_id == room_id) &
                (MembershipRequest.username == username) &
                (MembershipRequest.status == "pending")
            )
            membership_request_result = session.execute(membership_request).scalar_one_or_none()
            if membership_request_result is not None:
                raise HTTPException(status_code=400, detail="Already requested to join the room.")


            membership_request = MembershipRequest(
                room_id=room_id,
                username=username,
                status="pending",
                request_type="join_request",
                created_by=username,
            )
            session.add(membership_request)
            session.commit()

        return {"message": f"Join request sent for room {room_id} by {username} to approve"}

    async def create_room_membership(self, room_membership: RoomMembershipDTO):

        with Session(engine) as session:
            room_membership_obj = RoomMembership(
                room_id=room_membership.room_id,
                username=room_membership.username,
                last_read_at=room_membership.last_read_at,
                last_read_message_id=room_membership.last_read_message_id
            )
            session.add(room_membership_obj)
            session.commit()
            room_membership_dto = RoomMembershipDTO.model_validate(room_membership_obj)

        return room_membership_dto

    async def register_user(self, user_info: UserCreate):
        with Session(engine) as session:
            existing_user = session.get(User, user_info.username)
            if existing_user is not None:
                raise HTTPException(status_code=409, detail="User already exists")
            hashed_password = hash_password(user_info.password)
            user = User(
                username=user_info.username,
                password=hashed_password,
                fullname=user_info.fullname,
                email=user_info.email,
                rooms=[],
                avatar=user_info.avatar,
                pic_url=user_info.pic_url
            )
            session.add(user)
            session.commit()

        return {
            "message": f"User created successfully: {user_info.username}",
            "status_code": status.HTTP_201_CREATED,
        }

    async def login(self, user_info: UserLogin):
        with Session(engine) as session:
            user = session.get(User, user_info.username)
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid username")
            if user.password != hash_password(user_info.password):
                raise HTTPException(status_code=401, detail="Invalid password")
            access_token = create_access_token(user_info.username)
            refresh_token = create_access_token(user_info.username, timedelta(days=30))

        print("access_token ", access_token)
        print("refresh_token ", refresh_token)

        return {
            "message": f"User logged in successfully: {user_info.username}",
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


    async def get_user_profile(self, username: str):
        with Session(engine) as session:
            user = session.get(User, username)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            user_dto = UserSchema.model_validate(user)
            return user_dto

    async def update_user_profile(self, update_user: UpdateUserDTO, username: str):
        with Session(engine) as session:
            try:
                user = session.get(User, username)

                if update_user.avatar:
                    user.avatar = update_user.avatar
                if update_user.email:
                    user.email = update_user.email
                if update_user.fullname:
                    user.fullname = update_user.fullname
                if update_user.pic_url:
                    user.pic_url = update_user.pic_url

                session.add(user)
                session.commit()
                print("user_data", user)
                print("user_pic_url ", user.pic_url)
                return user
            except Exception:
                raise HTTPException(status_code=404, detail="User not found")


    async def get_all_users(self):
        with Session(engine) as session:
            try:
                users = select(User)
                users = session.execute(users).scalars().all()
                user_dtos = [UserSchema.model_validate(user) for user in users]
            except Exception:
                raise HTTPException(status_code=404, detail="No users found")
        return user_dtos

    async def get_all_rooms(self):
        with Session(engine) as session:
            try:
                rooms = select(Room)

                rooms = session.execute(rooms).scalars().all()
                room_dtos = [RoomSchema.model_validate(room) for room in rooms]
            except Exception:
                raise HTTPException(status_code=404, detail="No rooms found")
        return room_dtos


    async def get_messages(self, room_id: str):
        with Session(engine) as session:

            room_messages = select(Message).where(Message.room_id == room_id)
            room_messages = session.execute(room_messages).scalars().all()
            # for msg in room_messages:
            msg_dtos = [MessageSchema.model_validate(msg) for msg in room_messages]
            sorted_msg_dtos = sorted(msg_dtos, key=lambda x: x.timestamp)

        return sorted_msg_dtos

    async def send_message(self, content: Optional[str] = Form(None),
                           room_id: str = Form(...),
                           file: Optional[UploadFile] = File(None),
                           username: str = Depends()):

        with Session(engine) as session:
            try:
                user = session.get(User, username)
                room = session.get(Room, room_id)

            except Exception:
                raise HTTPException(status_code=404, detail="User/room not found")

            file_url = None
            if file:
                print("**********File Uploaded**********")
                ext = os.path.splitext(file.filename)[1]
                fname = f"{file.filename}{ext}"
                file_path = os.path.join(UPLOAD_DIR, fname)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                file_url = f"/{UPLOAD_DIR}/{fname}"

            # Save message
            message_item = Message(
                message_id=str(uuid.uuid4()),
                content=content,
                username=user.username,
                room_id=room_id,
                file_url=file_url
            )
            # message_item.save()
            session.add(message_item)
            print("file_url ", file_url)
            # Save UserMessage Info
            user_message_item = UserMessage(
                message_id=message_item.message_id,
                username=user.username
            )
            session.add(user_message_item)
            session.commit()

        return message_item

    async def get_all_messages(self):
        with Session(engine) as session:
            try:
                messages = select(Message)
                messages = session.execute(messages).scalars().all()
                message_dtos = [MessageSchema.model_validate(msg) for msg in messages]
                return message_dtos
            except Exception:
                raise HTTPException(status_code=404, detail="No messages found")


    async def get_message_last_seen_info(self, room_id: str):
        with Session(engine) as session:
            try:
                messages = select(Message).where(Message.room_id == room_id)
                messages = session.execute(messages).scalars().all()
                message_dtos = [MessageSchema.model_validate(msg) for msg in messages]
                return message_dtos
            except Exception:
                raise HTTPException(status_code=404, detail="No messages found")

    async def get_all_invitees_and_join_requests(self):
        with Session(engine) as session:
            try:
                membership_requests = select(MembershipRequest)
                membership_requests = session.execute(membership_requests).scalars().all()
                membership_requests_dtos = [MembershipRequestSchema.model_validate(membership_request)
                                            for membership_request in membership_requests]
            except Exception:
                raise HTTPException(status_code=404, detail="No membership requests found")
            return membership_requests_dtos