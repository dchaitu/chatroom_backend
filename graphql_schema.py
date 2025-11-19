import graphene
from datetime import datetime
from typing import Optional

# Enums
class MessageType(graphene.Enum):
    TEXT = "text"
    FILE = "file"

class RequestType(graphene.Enum):
    INVITE = "invite"
    JOIN_REQUEST = "join_request"

class RequestStatus(graphene.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

# Types
class UserType(graphene.ObjectType):
    username = graphene.String(required=True)
    fullname = graphene.String(required=True)
    email = graphene.String(required=True)
    avatar = graphene.String(default_value='😁')
    pic_url = graphene.String()
    rooms = graphene.List(lambda: RoomType)

    def resolve_rooms(self, info):
        # This would be implemented to fetch rooms for the user
        pass

class RoomType(graphene.ObjectType):
    room_id = graphene.ID(required=True)
    room_name = graphene.String(required=True)
    description = graphene.String()
    users = graphene.List(UserType)
    admins = graphene.List(UserType)
    messages = graphene.List(lambda: MessageType, limit=graphene.Int())

    def resolve_users(self, info):
        # Implementation to fetch users in the room
        pass

    def resolve_admins(self, info):
        # Implementation to fetch admins of the room
        pass

    def resolve_messages(self, info, limit=50):
        # Implementation to fetch messages in the room with pagination
        pass

class MessageType(graphene.ObjectType):
    message_id = graphene.ID(required=True)
    content = graphene.String()
    message_type = graphene.Field(MessageType, default_value=MessageType.TEXT)
    username = graphene.String(required=True)
    user = graphene.Field(UserType)
    room_id = graphene.ID(required=True)
    room = graphene.Field(RoomType)
    timestamp = graphene.DateTime(required=True)
    file_url = graphene.String()
    replies = graphene.List(lambda: ReplyType)
    reactions = graphene.List(lambda: ReactionType)

    def resolve_user(self, info):
        # Implementation to fetch user who sent the message
        pass

    def resolve_room(self, info):
        # Implementation to fetch room where message was sent
        pass

    def resolve_replies(self, info):
        # Implementation to fetch replies to this message
        pass

    def resolve_reactions(self, info):
        # Implementation to fetch reactions to this message
        pass

class ReplyType(graphene.ObjectType):
    reply_id = graphene.ID(required=True)
    thread_id = graphene.ID(required=True)
    message_id = graphene.ID(required=True)
    content = graphene.String(required=True)
    username = graphene.String(required=True)
    user = graphene.Field(UserType)
    timestamp = graphene.DateTime(required=True)

    def resolve_user(self, info):
        # Implementation to fetch user who sent the reply
        pass

class ReactionType(graphene.ObjectType):
    message_id = graphene.ID(required=True)
    username = graphene.String(required=True)
    user = graphene.Field(UserType)
    reaction_type = graphene.String(required=True)
    reacted_at = graphene.DateTime(required=True)

    def resolve_user(self, info):
        # Implementation to fetch user who reacted
        pass

class MembershipRequestType(graphene.ObjectType):
    room_id = graphene.ID(required=True)
    room = graphene.Field(RoomType)
    username = graphene.String(required=True)
    user = graphene.Field(UserType)
    request_type = graphene.Field(RequestType, required=True)
    status = graphene.Field(RequestStatus, required=True)
    created_by = graphene.String(required=True)
    created_by_user = graphene.Field(UserType)
    created_at = graphene.DateTime(required=True)

    def resolve_room(self, info):
        # Implementation to fetch the room
        pass

    def resolve_user(self, info):
        # Implementation to fetch the user
        pass

    def resolve_created_by_user(self, info):
        # Implementation to fetch the user who created the request
        pass

# Input Types
class UserInput(graphene.InputObjectType):
    username = graphene.String(required=True)
    password = graphene.String(required=True)
    fullname = graphene.String(required=True)
    email = graphene.String(required=True)
    avatar = graphene.String(default_value='😁')
    pic_url = graphene.String()

class RoomInput(graphene.InputObjectType):
    room_name = graphene.String(required=True)
    description = graphene.String()
    user_ids = graphene.List(graphene.ID)

class MessageInput(graphene.InputObjectType):
    content = graphene.String()
    room_id = graphene.ID(required=True)
    file_url = graphene.String()
    reply_to = graphene.ID()

class MembershipRequestInput(graphene.InputObjectType):
    room_id = graphene.ID(required=True)
    username = graphene.String(required=True)
    request_type = graphene.Argument(RequestType, required=True)

# Query and Mutation classes will be implemented in the next steps
class Query(graphene.ObjectType):
    # Placeholder for query definitions
    pass

class Mutation(graphene.ObjectType):
    # Placeholder for mutation definitions
    pass

# Create schema
schema = graphene.Schema(query=Query, mutation=Mutation)
