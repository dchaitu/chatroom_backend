import uuid
from datetime import datetime

import factory

from schemas import (
    RoomSchema, RoomDTO, UserCreate, RoomCreate, RoomUpdate, MakeRoomAdmin, UserLogin,
    UserSchema, UpdateUserDTO, UserRoomSchema, ConnectionSchema,
    MessageSchema, MessageCreate, SendMessage, MembershipRequestSchema,
    UserActionDTO, AddUserToRoomDTO, RoomMembershipDTO, MessageInfoDTO,
    ReplyMessageDTO, ReplyThreadDTO, ReactionDTO, UserReactionDTO,
    MessageResponse
)


class RoomSchemaFactory(factory.Factory):
    class Meta:
        model = RoomSchema

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Sequence(lambda n: "room_{}".format(n + 1))
    description = factory.Sequence(lambda n: "description_{}".format(n + 1))
    users = factory.List(
        [
            factory.Faker("user_name"),
            factory.Faker("user_name"),
        ]
    )


class RoomDTOFactory(factory.Factory):
    class Meta:
        model = RoomDTO

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Faker("company")
    description = factory.Faker("sentence")


class UserCreateFactory(factory.Factory):
    class Meta:
        model = UserCreate

    username = factory.Faker("user_name")
    password = factory.Faker("password")
    fullname = factory.Faker("name")
    email = factory.Faker("email")
    avatar = factory.Faker("emoji")
    recaptcha_token = factory.Faker("md5")
    pic_url = factory.Faker("url")


class RoomCreateFactory(factory.Factory):
    class Meta:
        model = RoomCreate

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Faker("company")
    description = factory.Faker("sentence")


class RoomUpdateFactory(factory.Factory):
    class Meta:
        model = RoomUpdate
    
    # RoomUpdate only has pass, but typically would have optional fields from RoomDTO
    # Since it's 'pass', it relies on BaseModel behavior or inheritance if it had any (it inherits BaseModel directly in schemas.py:25)
    # Actually looking at schemas.py:25: class RoomUpdate(BaseModel): pass
    # It seems empty.
    pass


class MakeRoomAdminFactory(factory.Factory):
    class Meta:
        model = MakeRoomAdmin

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Faker("user_name")


class UserLoginFactory(factory.Factory):
    class Meta:
        model = UserLogin

    username = factory.Faker("user_name")
    password = factory.Faker("password")
    recaptcha_token = factory.Faker("md5")


class UserSchemaFactory(factory.Factory):
    class Meta:
        model = UserSchema

    username = factory.Faker("user_name")
    fullname = factory.Faker("name")
    email = factory.Faker("email")
    avatar = factory.Faker("emoji")
    pic_url = factory.Faker("url")
    password = factory.Faker("password")


class UpdateUserDTOFactory(factory.Factory):
    class Meta:
        model = UpdateUserDTO

    avatar = factory.Faker("emoji")
    fullname = factory.Faker("name")
    email = factory.Faker("email")
    pic_url = factory.Faker("url")


class UserRoomSchemaFactory(factory.Factory):
    class Meta:
        model = UserRoomSchema

    username = factory.Faker("user_name")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))


class ConnectionSchemaFactory(factory.Factory):
    class Meta:
        model = ConnectionSchema

    connection_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Faker("user_name")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    connected_at = factory.LazyFunction(datetime.utcnow)


class MessageSchemaFactory(factory.Factory):
    class Meta:
        model = MessageSchema

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content = factory.Faker("sentence")
    username = factory.Faker("user_name")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    timestamp = factory.LazyFunction(datetime.utcnow)
    file_url = factory.Faker("url")


class MessageCreateFactory(factory.Factory):
    class Meta:
        model = MessageCreate

    content = factory.Faker("sentence")
    username = factory.Faker("user_name")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    file_url = factory.Faker("url")


class SendMessageFactory(factory.Factory):
    class Meta:
        model = SendMessage

    content = factory.Faker("sentence")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))


class MembershipRequestSchemaFactory(factory.Factory):
    class Meta:
        model = MembershipRequestSchema

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Faker("user_name")
    request_type = factory.Iterator(['invite', 'join_request'])
    status = factory.Iterator(['pending', 'accepted', 'rejected'])
    created_by = factory.Faker("user_name")
    created_at = factory.LazyFunction(datetime.utcnow)


class UserActionDTOFactory(factory.Factory):
    class Meta:
        model = UserActionDTO

    requested_user = factory.Faker("user_name")
    action = factory.Iterator(['approve', 'reject'])


class AddUserToRoomDTOFactory(factory.Factory):
    class Meta:
        model = AddUserToRoomDTO

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    added_user = factory.Faker("user_name")


class RoomMembershipDTOFactory(factory.Factory):
    class Meta:
        model = RoomMembershipDTO

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Faker("user_name")
    last_read_at = factory.LazyFunction(datetime.utcnow)
    last_read_message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))


class MessageInfoDTOFactory(factory.Factory):
    class Meta:
        model = MessageInfoDTO

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    username = factory.Faker("user_name")
    read_at = factory.LazyFunction(datetime.utcnow)


class ReplyMessageDTOFactory(factory.Factory):
    class Meta:
        model = ReplyMessageDTO

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content = factory.Faker("sentence")


class ReplyThreadDTOFactory(factory.Factory):
    class Meta:
        model = ReplyThreadDTO

    thread_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    reply_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content = factory.Faker("sentence")
    username = factory.Faker("user_name")
    timestamp = factory.LazyFunction(datetime.utcnow)


class ReactionDTOFactory(factory.Factory):
    class Meta:
        model = ReactionDTO

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    reaction_type = factory.Faker("emoji")


class UserReactionDTOFactory(factory.Factory):
    class Meta:
        model = UserReactionDTO

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    reaction_type = factory.Faker("emoji")
    username = factory.Faker("user_name")
    reacted_at = factory.LazyFunction(datetime.utcnow)


class MessageResponseFactory(factory.Factory):
    class Meta:
        model = MessageResponse

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content = factory.Faker("sentence")
    username = factory.Faker("user_name")
    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    timestamp = factory.LazyFunction(datetime.utcnow)
    file_url = factory.Faker("url")