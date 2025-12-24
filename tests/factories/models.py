import uuid
from datetime import timezone, datetime

import factory

from models.rds_models import (
    User, Room, RoomMembership, Message, MembershipRequest, 
    UserMessage, ReplyThread, UserReaction, Connection
)
from tests.factories.base import BaseFactory


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "user_{}".format(n + 1))
    password = factory.Faker("password")
    fullname = factory.Sequence(lambda n: "fullname_{}".format(n + 1))
    email = factory.Sequence(lambda n: "email_{}@gmail.com".format(n + 1))
    avatar = "😁"
    pic_url = factory.Faker("url")


class RoomFactory(BaseFactory):
    class Meta:
        model = Room

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Sequence(lambda n: "room_{}".format(n + 1))
    description = factory.Sequence(lambda n: "description_{}".format(n + 1))


class RoomMembershipFactory(BaseFactory):
    class Meta:
        model = RoomMembership

    id = factory.Sequence(lambda n:  n+1)
    room_id = factory.Sequence(lambda n:  "room_{}".format(n + 1))
    username = factory.Sequence(lambda n: "user_{}".format(n + 1))
    is_admin = factory.Iterator([True, False])
    joined_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    last_read_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    last_read_message_id = factory.Sequence(lambda n:  "message_{}".format(n + 1))


class MessageFactory(BaseFactory):
    class Meta:
        model = Message

    message_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    content = factory.Faker("text")
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    file_url = factory.Faker("url")


class MembershipRequestFactory(BaseFactory):
    class Meta:
        model = MembershipRequest

    id = factory.Sequence(lambda n: n + 1)
    room_id = factory.Sequence(lambda n: "room_{}".format(n + 1))
    username = factory.Faker("first_name")
    request_type = factory.Iterator(['invite', 'join_request'])
    status = factory.Iterator(['pending', 'accepted', 'rejected'])
    created_by = factory.Sequence(lambda n: f"creator_{n + 1}")
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class UserMessageFactory(BaseFactory):
    class Meta:
        model = UserMessage

    message = factory.SubFactory(MessageFactory)
    user = factory.SubFactory(UserFactory)


class ReplyThreadFactory(BaseFactory):
    class Meta:
        model = ReplyThread

    thread_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    reply_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    message = factory.SubFactory(MessageFactory)
    content = factory.Faker("text")
    user = factory.SubFactory(UserFactory)


class UserReactionFactory(BaseFactory):
    class Meta:
        model = UserReaction

    message = factory.SubFactory(MessageFactory)
    user = factory.SubFactory(UserFactory)
    reaction_type = factory.Faker("emoji")


class ConnectionFactory(BaseFactory):
    class Meta:
        model = Connection

    connection_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)