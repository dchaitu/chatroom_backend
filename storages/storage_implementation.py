import os
import shutil
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, status, Form, Depends, UploadFile, File

from constants import hash_password, create_access_token, get_current_user
from interactors.storage_interfaces.storage_interface import StorageInterface
from models.pynamo_models import Room, MembershipRequest, RoomMembership, User, UserReaction, Message, ReplyThread, UserMessage
from constants import UPLOAD_DIR
from schemas import MakeRoomAdmin, UserActionDTO, ReactionDTO, ReplyThreadDTO, ReplyMessageDTO, RoomMembershipDTO, \
    RoomCreate, AddUserToRoomDTO, RoomSchema, RoomUpdate, UserCreate, UserLogin, UpdateUserDTO, MessageSchema


class StorageImplementation(StorageInterface):

    async def create_room_admin(self, room_admin: MakeRoomAdmin):
        try:
            room = Room.get(room_admin.room_id)
            room.admins.append(room_admin.username)
            room.save()

        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

        return room

    async def get_pending_requests(self, request_type: str, username: str):
        """Get all pending requests invite/join_request for rooms from other users to the admin"""
        # Get all rooms where user is admin
        pending_requests = list(MembershipRequest.scan(
            filter_condition=(MembershipRequest.status == "pending") & (MembershipRequest.request_type == request_type)
        ))
        room_ids = {req.room_id for req in pending_requests}
        print(f'room_ids: {room_ids}')
        #  Rooms for which user is admin
        rooms = {room.room_id: room for room in Room.batch_get(room_ids)}

        print(f"len of user_invitees_rooms: {len(pending_requests)}")
        filtered_pending_requests = [req for req in pending_requests
                                     if username in rooms.get(req.room_id, Room()).admins
                                     ]
        print(f"filtered_pending_requests: {filtered_pending_requests}")

        return filtered_pending_requests

    async def admin_respond_to_room_membership_request(self,
            room_id: str,
            user_action: UserActionDTO,
            current_user: str,
    ):
        """Admin accepts or rejects a room joining request"""
        try:
            room = Room.get(room_id)
            if current_user not in room.admins:
                raise HTTPException(status_code=403, detail="Only admins can respond to requests")
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

        action = user_action.action
        user_invited = user_action.requested_user
        try:
            print("Received room membership request response:")
            print("Check if invite exists")
            member_request = MembershipRequest.get(room_id, user_invited)
        except MembershipRequest.DoesNotExist:
            raise HTTPException(status_code=404, detail="Invite not found")

        # Verify the responding user is an admin of the room

        if action == "accept":
            # Add user to room
            if user_invited not in room.users:
                room.users.append(user_invited)
                room.save()
                print(f"Room {room.room_name} added {user_invited} as member")
                # Update invite status
                user = User.get(user_invited)
                user.rooms.append(room_id)
                user.save()
                print(f"**User {user_invited} added to room {room_id}")
                RoomMembership(room_id=room_id, username=user_invited).save()

        member_request.status = "accepted" if action == "accept" else "rejected"
        member_request.save()

        return {
            "message": f"{action} Performed successfully on {user_invited} for room {room_id}"
        }

    # reaction_routers

    async def create_reaction_to_message(self, reaction: ReactionDTO, username: str):
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

    async def get_reactions_to_messages_in_room(self, room_id: str):
        messages_in_room = list(Message.scan(Message.room_id == room_id))
        message_ids = [message.message_id for message in messages_in_room]
        reactions = []
        for message in messages_in_room:
            reactions.extend(list(UserReaction.query(message.message_id)))

        return reactions

    async def get_all_reactions(self):
        reactions = list(UserReaction.scan())
        return reactions

    # reply_routers

    async def create_reply_to_message(self, reply_message: ReplyMessageDTO, username: str):
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

    async def get_message_reply_count(self, message_id: str):
        replies_for_message = list(ReplyThread.scan(filter_condition=(ReplyThread.message_id == message_id)))
        return {message_id: len(replies_for_message)}

    async def get_all_message_reply_count(self):
        replies_for_message = list(ReplyThread.scan())
        message_wise_replies_count = defaultdict(int)
        for reply in replies_for_message:
            message_wise_replies_count[reply.message_id] += 1
        return message_wise_replies_count

    async def show_replies_for_messages(self, message_id: str):
        replies_for_message = list(ReplyThread.scan(filter_condition=(ReplyThread.message_id == message_id)))
        print(f'replies_for_message {replies_for_message}')
        replies_for_message.sort(key=lambda r: r.timestamp)
        return replies_for_message

    async def show_all_replies(self)->List[ReplyThreadDTO]:
        all_replies = list(ReplyThread.scan())
        return all_replies

    # room_router

    async def create_room(self, room: RoomCreate, username: str ):
        try:
            user = User.get(username)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            existing_room = Room.get(room.room_id)
            raise HTTPException(status_code=400, detail="Room already exists")

        except Room.DoesNotExist:
            pass

        room_item = Room(
            room_id=room.room_id,
            room_name=room.room_name.strip(' '),
            users=[username],
            description=room.description,
            admins=[username],
        )
        room_item.save()

        user.rooms.append(room.room_id)
        user.save()
        return {"message": f"Room created successfully: {room.room_id} by {username}"}

    async def update_room(self, room: RoomUpdate, username: str ):
        try:
            user = User.get(username)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            existing_room = Room.get(room.room_id)
            if room.room_name:
                existing_room.room_name = room.room_name
            if room.description:
                existing_room.description = room.description
            existing_room.save()
            return {"message": f"Updated Room fields successfully: {room.room_name}"}

        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

    async def user_leave_room(self, room_id: str, username: str ):
        try:
            user = User.get(username)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            room = Room.get(room_id)
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

        if room_id in user.rooms:
            user.rooms.remove(room_id)
            user.save()

        if username in room.users:
            room.users.remove(username)
            room.save()

        return {"message": f"{user.username} has left the room {room.room_name}"}

    async def mark_as_read(self, room_id: str, username: str ):
        """Update last_read_at when user opens a room"""
        membership = RoomMembership.get(room_id, username)
        membership.last_read_at = datetime.now(timezone.utc)
        membership.save()
        room_messages = list(Message.scan(Message.room_id == room_id))
        for msg in room_messages:
            try:
                UserMessage.get(msg.message_id, username)
            except UserMessage.DoesNotExist:
                user_message = UserMessage(
                    message_id=msg.message_id,
                    username=username,
                    read_at=datetime.now(timezone.utc)
                )
                user_message.save()

        return {"message": "Marked as read"}

    async def get_unread_counts(self, room_ids: List[str], username: str ):
        """Get count of unread messages for a user in each room"""
        memberships = list(RoomMembership.scan(RoomMembership.username == username))

        # Step 2: Filter memberships to only requested room_ids
        memberships = [m for m in memberships if m.room_id in room_ids]
        unread_counts = []

        for membership in memberships:
            last_read_at = membership.last_read_at

            unread_messages = list(Message.scan(
                (Message.room_id == membership.room_id) & (Message.timestamp > last_read_at)
            ))

            # unread_counts[membership.room_id] = len(unread_messages)
            unread_counts.append({"room_id": membership.room_id, "count": len(unread_messages)})

        return unread_counts

    async def get_user_rooms(self, username: str )-> List[RoomSchema] :
        print(f"Received rooms request: {username}")
        try:
            user = User.get(username)
            print(f"User rooms: {user.rooms}, user {user.username}")
        except User.DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        room_ids = user.rooms
        rooms = []
        room_ids = list(set([room_id for room_id in room_ids]))
        for room_id in room_ids:
            try:
                room = Room.get(room_id)
                rooms.append(room)
            except Room.DoesNotExist:
                continue
        room_dtos = [RoomSchema.from_orm(room) for room in rooms]
        return room_dtos

    async def get_available_rooms(self, username: str ):
        """Rooms in which user is not a member"""
        user = User.get(username)
        current_rooms = list(Room.batch_get(user.rooms))
        print(f"current_rooms :- {[room.room_name for room in current_rooms]}")
        print(f"user.rooms :- {user.rooms}")
        all_rooms = list(Room.scan())
        available_rooms = [r for r in all_rooms if r.room_id not in user.rooms]
        print(f"available_rooms :- {[room.room_name for room in available_rooms]}")
        return available_rooms

    async def get_room_details(self, room_id: str):
        try:
            room = Room.get(room_id)
            return room
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")
        except Exception as e:
            print("Error in /room_details:", e, flush=True)
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def admin_add_user_to_room(self,
            add_user_to_room: AddUserToRoomDTO, current_user: str
    ):
        """Admin invites a user to join a room."""
        room_id = add_user_to_room.room_id
        invited_user = add_user_to_room.added_user
        try:
            room = Room.get(room_id)
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

        if current_user not in room.admins:
            raise HTTPException(
                status_code=403, detail="Only admins can invite users to this room."
            )

        # Check if user already in room
        if invited_user in room.users:
            raise HTTPException(status_code=400, detail="User already in room.")

        # Create invite

        membership_request = MembershipRequest(
            room_id=room_id,
            username=invited_user,
            status="pending",
            request_type="invite",
            created_by=current_user,
        )
        membership_request.save()
        return {"message": f"Invite sent to {invited_user} for room {room_id}"}

    async def user_request_join_room(self, room_id: str, username: str ):
        """User wants to join a room."""
        try:
            room = Room.get(room_id)
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

        # Check if already a member
        if username in room.users:
            raise HTTPException(status_code=400, detail="Already a member of the room.")

        # Check if already requested to join the room
        try:
            membership_request = MembershipRequest.get(room_id, username)
            if membership_request.status == "pending":
                raise HTTPException(
                    status_code=400, detail="Already requested to join the room."
                )
        except:
            pass

        # Create join request
        membership_request = MembershipRequest(
            room_id=room_id,
            username=username,
            status="pending",
            request_type="join_request",
            created_by=username,
        )
        membership_request.save()
        return {"message": f"Join request sent for room {room_id} by {username} to approve"}

    async def create_room_membership(self, room_membership: RoomMembershipDTO):
        room_member = RoomMembership(room_id=room_membership.room_id,
                                     username=room_membership.username,
                                     last_read_at=room_membership.last_read_at,
                                     last_read_message_id=room_membership.last_read_message_id)
        room_member.save()
        return room_member

    async def register_user(self, user_info: UserCreate):
        print(f"Received registration request: {user_info}", flush=True)

        # Skip reCAPTCHA for testing - add back later
        # is_valid_captcha = await verify_recaptcha(user_info.recaptcha_token)
        # if not is_valid_captcha:
        #     raise HTTPException(status_code=400, detail="Invalid reCAPTCHA")

        try:
            existing_user = User.get(user_info.username)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )
        except User.DoesNotExist:
            pass

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
        user.save()

        return {
            "message": f"User created successfully: {user_info.username}",
            "status_code": status.HTTP_201_CREATED,
        }

    async def login(self, user_info: UserLogin):

        try:
            user = User.get(user_info.username)
        except User.DoesNotExist:
            raise HTTPException(detail="Invalid username", status_code=401)

        if user.password != hash_password(user_info.password):
            raise HTTPException(detail="Invalid password", status_code=401)

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
        try:
            user = User.get(username)
            print("get user_data", user)
            return user
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

    async def update_user_profile(self, update_user: UpdateUserDTO, username: str):
        try:
            user = User.get(username)
            if update_user.avatar:
                user.avatar = update_user.avatar
            if update_user.email:
                user.email = update_user.email
            if update_user.fullname:
                user.fullname = update_user.fullname
            if update_user.pic_url:
                user.pic_url = update_user.pic_url

            user.save()
            print("user_data", user)
            print("user_pic_url ", user.pic_url)
            return user
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

    async def get_all_users(self):
        try:
            users = list(User.scan())
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="No users found")
        return users

    async def get_all_rooms(self):
        try:
            rooms = list(Room.scan())
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="No rooms found")
        return rooms

    async def get_messages(self, room_id: str):
        print(f"Get messages request: {room_id}")
        messages = list(Message.scan(Message.room_id == room_id))
        for msg in messages:
            print(f"Message info: {msg.content}- {msg.timestamp}")
        messages_in_room = [
            MessageSchema(
                **{
                    "message_id": msg.message_id,
                    "content": msg.content,
                    "username": msg.username,
                    "room_id": msg.room_id,
                    "timestamp": msg.timestamp,
                    "file_url": msg.file_url
                }
            )
            for msg in messages
        ]
        messages_in_room = sorted(messages_in_room, key=lambda x: x.timestamp)
        return messages_in_room

    async def send_message(self, content: Optional[str] = Form(None),
                           room_id: str = Form(...),
                           file: Optional[UploadFile] = File(None),
                           username: str = Depends(get_current_user)):
        try:
            user = User.get(username)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            room = Room.get(room_id)
        except Room.DoesNotExist:
            raise HTTPException(status_code=404, detail="Room not found")

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
        message_item.save()
        print("file_url ", file_url)
        # Save UserMessage Info
        user_message_item = UserMessage(
            message_id=message_item.message_id,
            username=user.username
        )
        user_message_item.save()

        return message_item

    def get_all_messages(self):
        try:
            messages = list(Message.scan())
            messages = sorted(messages, key=lambda x: x.timestamp)
        except Message.DoesNotExist:
            raise HTTPException(status_code=404, detail="No messages found")

        return messages

    def get_message_last_seen_info(self, room_id: str):
        try:
            message_info_list = []
            room_messages = list(Message.scan(Message.room_id == room_id))
            for msg in room_messages:
                message_info = list(UserMessage.query(msg.message_id))
                print("message_info ", message_info)
                # return message_info
                # message_info = MessageInfoDTO(
                #     message_id=msg.message_id,
                #     username=msg.username,
                #     read_at=msg.read_at if hasattr(msg, "read_at") else msg.timestamp
                # )
                message_info_list.extend(message_info)

            print("message_info_list ", message_info_list)
            return message_info_list

        except UserMessage.DoesNotExist:
            raise HTTPException(status_code=404, detail="No messages found")

    # invitee and join requests
    async def get_all_invitees_and_join_requests(self):
        try:
            membership_requests = list(MembershipRequest.scan())
        except MembershipRequest.DoesNotExist:
            raise HTTPException(status_code=404, detail="No rooms found")
        return membership_requests