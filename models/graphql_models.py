import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from sqlalchemy.orm import Session

from models.rds_models import User, Room, Message, MembershipRequest, RoomMembership, UserMessage, ReplyThread, \
    UserReaction, engine


class UserType(SQLAlchemyObjectType):
    class Meta:
        model = User

class RoomType(SQLAlchemyObjectType):
    class Meta:
        model = Room

class MessageType(SQLAlchemyObjectType):
    class Meta:
        model = Message

class MembershipRequestType(SQLAlchemyObjectType):
    class Meta:
        model = MembershipRequest

class RoomMembershipType(SQLAlchemyObjectType):
    class Meta:
        model = RoomMembership

class UserMessageType(SQLAlchemyObjectType):
    class Meta:
        model = UserMessage


class ReplyThreadType(SQLAlchemyObjectType):
    class Meta:
        model = ReplyThread

class UserReactionType(SQLAlchemyObjectType):
    class Meta:
        model = UserReaction


class Query(graphene.ObjectType):
    all_users = graphene.List(UserType)
    all_rooms = graphene.List(RoomType)
    all_messages = graphene.List(MessageType)
    all_membership_requests = graphene.List(MembershipRequestType)
    all_room_memberships = graphene.List(RoomMembershipType)
    all_user_messages = graphene.List(UserMessageType)
    all_reply_threads = graphene.List(ReplyThreadType)
    all_user_reactions = graphene.List(UserReactionType)

    def resolve_hello(root, info, name):
        return f"Hello {name}!"

    def resolve_all_users(self, info):
        with Session(engine) as session:
            return session.query(User).all()

    def resolve_all_rooms(self, info):
        with Session(engine) as session:
            return session.query(Room).all()

    def resolve_all_messages(self, info):
        with Session(engine) as session:
            return session.query(Message).all()

    def resolve_all_membership_requests(self, info):
        with Session(engine) as session:
            return session.query(MembershipRequest).all()

    def resolve_all_room_memberships(self, info):
        with Session(engine) as session:
            return session.query(RoomMembership).all()

    def resolve_all_user_messages(self, info):
        with Session(engine) as session:
            return session.query(UserMessage).all()

    def resolve_all_reply_threads(self, info):
        with Session(engine) as session:
            return session.query(ReplyThread).all()

    def resolve_all_user_reactions(self, info):
        with Session(engine) as session:
            return session.query(UserReaction).all()


schema = graphene.Schema(query=Query)
# Write your query or mutation here
# query{
#   allUsers{
#     username
#   }
# }