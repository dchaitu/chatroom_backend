import os
import shutil
import uuid
from collections import defaultdict
from datetime import timezone, datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status, Form, UploadFile, File, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from constants import hash_password, create_access_token, UPLOAD_DIR
from interactors.storage_interfaces.storage_interface import StorageInterface
from models.rds_models import User, engine, RoomMembership, Room, MembershipRequest, UserReaction, ReplyThread, Message, \
    UserMessage
from schemas import MakeRoomAdmin, RoomCreate, RoomUpdate, RoomSchema, AddUserToRoomDTO, RoomMembershipDTO, UserCreate, \
    UserLogin, UserSchema, UpdateUserDTO, MessageSchema, MembershipRequestSchema, UserActionDTO, ReactionDTO, \
    ReplyMessageDTO, ReplyThreadDTO, UserReactionDTO, RoomDTO, MessageInfoDTO


class RDSStorageImplementation(StorageInterface):
    async def create_room_admin(self, room_admin: MakeRoomAdmin) -> RoomSchema:
        room = select(Room).where(Room.room_id == room_admin.room_id)

        with Session(engine) as session:
            room = session.execute(room).scalar_one_or_none()
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")

            for membership in room.room_memberships:
                if membership.username == room_admin.username:
                    membership.is_admin = True
                    session.commit()
        print(f"User {room_admin.username} is now an admin of room {room.room_id}")
        return RoomSchema(
            room_id=room.room_id,
            room_name=room.room_name,
            description=room.description,
            users=[m.username for m in room.room_memberships],
        )

    async def get_pending_requests(self, request_type: str, username: str) -> List[MembershipRequestSchema]:
        with Session(engine) as session:
            admin_rooms = session.execute(
                select(Room.room_id).where((RoomMembership.username == username) & (RoomMembership.is_admin))
            ).scalars().all()

            if not admin_rooms:
                return []

            statement = select(MembershipRequest).where(
                (MembershipRequest.room_id.in_(admin_rooms)) &
                (MembershipRequest.request_type == request_type) &
                (MembershipRequest.status == "pending")
            )

            pending_requests = session.execute(statement).scalars().all()
            pending_requests_dtos = [MembershipRequestSchema.model_validate(request) for request in pending_requests]
            return pending_requests_dtos

    async def admin_respond_to_room_membership_request(
            self,
            room_id: str,
            user_action: UserActionDTO,
            current_user: str
    ) -> Dict[str, str]:
        with Session(engine) as session:
            action = user_action.action
            user_invited = user_action.requested_user

            membership_request = session.scalar(
                select(MembershipRequest).where(
                    (MembershipRequest.room_id == room_id)
                    & (
                            (MembershipRequest.username == user_invited)
                            | (MembershipRequest.created_by == user_invited)
                    )
                    & (MembershipRequest.status == "pending")
                )
            )

            if membership_request is None:
                raise HTTPException(status_code=404, detail=f"Membership request with room_id={room_id} not found")

            room = session.scalar(select(Room).where(Room.room_id == room_id))
            user = session.scalar(select(User).where(User.username == user_invited))

            if membership_request.request_type == "invite":
                if current_user != membership_request.username:
                    raise HTTPException(status_code=403, detail="Only the invited user can respond to an invite")

            elif membership_request.request_type == "join_request":
                is_user_admin = session.scalar(
                    select(RoomMembership.is_admin).where(
                        (RoomMembership.room_id == room_id)
                        & (RoomMembership.username == current_user)
                    )
                )
                if is_user_admin is None:
                    raise HTTPException(status_code=403, detail="Only an admin can respond to a join request")

            else:
                raise HTTPException(status_code=400, detail="Invalid request type")

            if action == "accept":
                membership_request.status = "accepted"

                if user not in room.users:
                    room.users.append(user)

                if room not in user.rooms:
                    user.rooms.append(room)

                session.add(RoomMembership(room_id=room.room_id, username=user.username))

            elif action == "reject":
                membership_request.status = "rejected"
            else:
                raise HTTPException(status_code=400, detail="Invalid action")

            if action == "accept":
                session.add(RoomMembership(room_id=room_id, username=user_invited))
            session.add(membership_request)
            session.commit()
        return {"message": f"Membership request {action} for user {user_invited} in room {room_id}"}


    async def create_reaction_to_message(self, reaction: ReactionDTO, username: str) -> UserReaction:
        with Session(engine) as session:
            user_reaction = session.execute(
                select(UserReaction).where(
                    (UserReaction.message_id == reaction.message_id) & (UserReaction.username == username)
                )
            ).scalar_one_or_none()

            if user_reaction:
                if user_reaction.reaction_type == reaction.reaction_type:
                    session.delete(user_reaction)
                    session.commit()
                    return user_reaction
                else:
                    user_reaction.reaction_type = reaction.reaction_type
                    user_reaction.reacted_at = datetime.now(timezone.utc)
            else:
                user_reaction = UserReaction(
                    message_id=reaction.message_id,
                    username=username,
                    reaction_type=reaction.reaction_type,
                    reacted_at=datetime.now(timezone.utc)
                )
                session.add(user_reaction)

            session.commit()
            session.refresh(user_reaction)
            return user_reaction

    async def get_reactions_to_messages_in_room(self, room_id: str) -> List[UserReactionDTO]:
        with Session(engine) as session:
            statement = select(UserReaction).join(Message).where(Message.room_id == room_id)
            reactions = session.execute(statement).scalars().all()
            return [UserReactionDTO.model_validate(reaction) for reaction in reactions]


    async def get_all_reactions(self) -> List[UserReaction]:
        statement = select(UserReaction)
        reactions = []
        with Session(engine) as session:
            reactions = session.execute(statement).scalars().all()
        return reactions

    async def create_reply_to_message(self, reply_message: ReplyMessageDTO, username: str) -> ReplyThreadDTO:
        with Session(engine) as session:
            reply_thread = ReplyThread(
                message_id=reply_message.message_id,
                content=reply_message.content,
                username=username,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(reply_thread)
            session.commit()
            reply_thread_dto = ReplyThreadDTO.model_validate(reply_thread)
        return reply_thread_dto

    async def get_message_reply_count(self, message_id: str) -> Dict[str, int]:
        statement = select(ReplyThread).where(ReplyThread.message_id == message_id)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
        return {message_id: len(replies_for_message)}

    async def get_all_message_reply_count(self) -> Dict[str, int]:
        statement = select(ReplyThread)
        message_wise_replies_count = defaultdict(int)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
            for reply in replies_for_message:
                message_wise_replies_count[reply.message_id] += 1

        return message_wise_replies_count

    async def show_replies_for_messages(self, message_id: str) -> List[ReplyThreadDTO]:
        statement = select(ReplyThread).where(ReplyThread.message_id == message_id)
        with Session(engine) as session:
            replies_for_message = session.execute(statement).scalars().all()
            replies_for_message.sort(key=lambda r: r.timestamp)

        return [ReplyThreadDTO.model_validate(reply) for reply in replies_for_message]

    async def show_all_replies(self) -> List[ReplyThreadDTO]:
        statement = select(ReplyThread)
        with Session(engine) as session:
            replies = session.execute(statement).scalars().all()
            # replies.sort(key=lambda r: r.timestamp)
        return [ReplyThreadDTO.model_validate(reply) for reply in replies]

    async def create_room(self, room: RoomCreate, username: str) -> Dict[str, str]:
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            check_room = session.get(Room, room.room_id)
            if check_room:
                raise HTTPException(status_code=400, detail="Room already exists")

            room_obj = Room(
                room_id=room.room_id,
                room_name=room.room_name.strip(' '),
                description=room.description,
                users=[user],
            )
            session.add(room_obj)
            session.commit()

            room_membership = RoomMembership(
                room_id=room.room_id,
                username=username,
                is_admin=True,
            )
            session.add(room_membership)
            session.commit()

        return {"message": f"Room created successfully: {room.room_id} by {username}"}

    async def update_room(self, room: RoomUpdate, username: str) -> Dict[str, str]:
        with Session(engine) as session:
            existing_room = session.get(Room, room.room_id)
            if existing_room is None:
                raise HTTPException(status_code=404, detail="Room not found")
            if room.room_name:
                existing_room.room_name = room.room_name
            if room.description:
                existing_room.description = room.description
            session.commit()
        return {"message": f"Updated Room fields successfully: {room.room_name}"}

    async def user_leave_room(self, room_id: str, username: str) -> None:
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            room = session.get(Room, room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")

            if room in user.rooms:
                user.rooms.remove(room)
                session.commit()

    async def mark_as_read(self, room_id: str, username: str) -> Dict[str, str]:
        """Update last_read_at when user opens a room"""
        with Session(engine) as session:
            membership = session.query(RoomMembership).filter_by(
                room_id=room_id,
                username=username
            ).first()

            if membership:
                membership.last_read_at = datetime.utcnow()
                session.commit()

        return {"status": "ok"}

    async def get_unread_counts(self, room_ids: List[str], username: str) -> List[Dict[str, Any]]:
        with Session(engine) as session:
            statement = select(RoomMembership).where(
                (RoomMembership.username == username) &
                (RoomMembership.room_id.in_(room_ids))
            )
            memberships = session.execute(statement).scalars().all()
            unread_counts = []
            for membership in memberships:
                last_read_at = membership.last_read_at
                if last_read_at:
                    count_statement = select(func.count(Message.message_id)).where(
                        (Message.room_id == membership.room_id) &
                        (Message.timestamp > last_read_at)
                    )
                    count = session.execute(count_statement).scalar_one()
                else:
                    count_statement = select(func.count(Message.message_id)).where(
                        Message.room_id == membership.room_id
                    )
                    count = session.execute(count_statement).scalar_one()
                unread_counts.append({"room_id": membership.room_id, "count": count})
        return unread_counts

    async def get_user_rooms(self, username: str) -> List[RoomSchema]:
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            rooms = user.rooms
            room_dtos = []
            for room in rooms:
                room_dtos.append(
                    RoomSchema(
                        room_id=room.room_id,
                        room_name=room.room_name,
                        description=room.description,
                        users=[user.username for user in room.users],
                    )
                )
        return room_dtos

    async def get_available_rooms(self, username: str) -> List[RoomSchema]:
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user_rooms = user.rooms
            all_rooms = session.execute(select(Room)).scalars().all()
            available_rooms = [room for room in all_rooms if room not in user_rooms]
            room_dtos = []
            for room in available_rooms:
                room_dtos.append(
                    RoomSchema(
                        room_id=room.room_id,
                        room_name=room.room_name,
                        description=room.description,
                        users=[user.username for user in room.users],
                    )
                )
        return room_dtos

    async def get_room_details(self, room_id: str) -> RoomSchema:
        with Session(engine) as session:
            room = session.get(Room, room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            room_dto = RoomSchema(
                room_id=room.room_id,
                room_name=room.room_name,
                description=room.description,
                users=[user.username for user in room.users],
            )
        return room_dto

    async def get_room_admins(self, room_id:str):
        with Session(engine) as session:
            admins = select(RoomMembership).where(
                (RoomMembership.room_id == room_id) & (RoomMembership.is_admin == True)
            )
            admins_result = session.execute(admins).scalars().all()
            if not admins_result:
                raise HTTPException(status_code=404, detail="Admin not found")
            admins = [user.username for user in admins_result]
        return admins

    async def admin_add_user_to_room(
            self,
            add_user_to_room: AddUserToRoomDTO, current_user: str
            ) -> Dict[str, str]:
        with Session(engine) as session:
            current_room_id = add_user_to_room.room_id
            existing_request = session.execute(
                select(MembershipRequest).where(
                    (MembershipRequest.room_id == current_room_id) &
                    (MembershipRequest.username == add_user_to_room.added_user) &
                    (MembershipRequest.status == "pending") &
                    (MembershipRequest.request_type == "invite")
                )
            ).scalar_one_or_none()

            if existing_request:
                raise HTTPException(status_code=400, detail="Invite already sent to this user.")

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
            if invited_user in room.users:
                raise HTTPException(status_code=400, detail="User already in room.")
            invited_username = invited_user.username

            membership_request = MembershipRequest(
                room_id=current_room_id,
                username=invited_username,
                status="pending",
                request_type="invite",
                created_by=current_user,
            )
            session.add(membership_request)
            session.commit()

        return {"message": f"Invite sent to {invited_username} for room {current_room_id}"}

    async def user_request_join_room(self, room_id: str, username: str) -> Dict[str, str]:
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

    async def create_room_membership(self, room_membership: RoomMembershipDTO) -> RoomMembershipDTO:

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

    async def register_user(self, user_info: UserCreate) -> Dict[str, Any]:
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

    async def login(self, user_info: UserLogin) -> Dict[str, Any]:
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

    async def get_user_profile(self, username: str) -> UserSchema:
        with Session(engine) as session:
            user = session.get(User, username)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            user_dto = UserSchema.model_validate(user)
            return user_dto

    async def update_user_profile(self, update_user: UpdateUserDTO, username: str) -> User:
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if update_user.avatar:
                user.avatar = update_user.avatar
            if update_user.email:
                user.email = update_user.email
            if update_user.fullname:
                user.fullname = update_user.fullname
            if update_user.pic_url:
                user.pic_url = update_user.pic_url

            session.commit()
            session.refresh(user)
            return user

    async def get_all_users(self) -> List[UserSchema]:
        with Session(engine) as session:
            users = session.execute(select(User)).scalars().all()
            user_dtos = [UserSchema.model_validate(user) for user in users]
        return user_dtos

    async def get_all_rooms(self) -> List[RoomSchema]:
        with Session(engine) as session:
            room_dtos = []
            rooms = session.execute(select(Room)).scalars().all()
            for room in rooms:
                room_dtos.append(
                    RoomSchema(
                        room_id=room.room_id,
                        room_name=room.room_name,
                        description=room.description,
                        users=[user.username for user in room.users],
                    )
                )
        return room_dtos

    async def get_messages(self, room_id: str) -> List[MessageSchema]:
        with Session(engine) as session:

            statement = select(Message).where(Message.room_id == room_id)
            room_messages = session.execute(statement).scalars().all()
            # for msg in room_messages:
            msg_dtos = [MessageSchema.model_validate(msg) for msg in room_messages]
            sorted_msg_dtos = sorted(msg_dtos, key=lambda x: x.timestamp)

        return sorted_msg_dtos

    async def send_message(self, content: Optional[str] = Form(None),
                           room_id: str = Form(...),
                           file: Optional[UploadFile] = File(None),
                           username: str = Depends()) -> MessageSchema:
        import boto3
        S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME","chatroom-s3-files")
        AWS_REGION = os.getenv("REGION_NAME","us-east-1")
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        with Session(engine) as session:
            user = session.get(User, username)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            room = session.get(Room, room_id)
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")

            file_url = None
            if file:
                print("**********File Uploaded**********")
                ext = os.path.splitext(file.filename)[1]
                fname = f"{uuid.uuid4()}{ext}"
                file_bytes = await file.read()
                try:
                    from boto3 import s3
                    # s3_client.put_object(
                    #     Bucket=S3_BUCKET_NAME,
                    #     Key=fname,
                    #     Body=file_bytes,
                    #     ContentType=file.content_type
                    # )
                    s3_client.upload_fileobj(
                        file.file,
                        S3_BUCKET_NAME,
                        f"uploads/{fname}",
                        ExtraArgs={"ContentType": file.content_type}
                    )
                    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/uploads/{fname}"
                    print(f"Uploaded to {file_url}")
                except Exception as e:
                    print(f"File upload error: {e}")
                    raise HTTPException(status_code=500, detail="Failed to upload file to S3")


            # Save message
            message_item = Message(
                message_id=str(uuid.uuid4()),
                content=content,
                username=user.username,
                room_id=room_id,
                file_url=file_url
            )
            session.add(message_item)
            print("file_url ", file_url)
            # Save UserMessage Info
            user_message_item = UserMessage(
                message_id=message_item.message_id,
                username=user.username
            )
            session.add(user_message_item)
            session.commit()
            msg_dto = MessageSchema.model_validate(message_item)


        return msg_dto

    async def get_all_messages(self) -> List[MessageSchema]:
        with Session(engine) as session:
            messages = session.execute(select(Message)).scalars().all()
            message_dtos = [MessageSchema.model_validate(msg) for msg in messages]
            return message_dtos

    async def get_message_last_seen_info(self, room_id: str) -> List[MessageInfoDTO]:
        with Session(engine) as session:
            room_messages = session.execute(select(Message).where(Message.room_id == room_id)).scalars().all()
            all_user_messages = []
            for msg in room_messages:
                user_message_statement = select(UserMessage).where(
                    UserMessage.message_id == msg.message_id
                )
                user_messages_for_msg = session.execute(user_message_statement).scalars().all()
                all_user_messages.extend(user_messages_for_msg)

            session.commit()

            message_dtos = [MessageInfoDTO.model_validate(msg) for msg in all_user_messages]
            return message_dtos

    async def get_all_invitees_and_join_requests(self) -> List[MembershipRequestSchema]:
        with Session(engine) as session:
            membership_requests = session.execute(select(MembershipRequest)).scalars().all()
            membership_requests_dtos = [MembershipRequestSchema.model_validate(membership_request)
                                        for membership_request in membership_requests]
            return membership_requests_dtos
