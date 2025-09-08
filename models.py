import logging
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, ListAttribute
from datetime import datetime, timezone, timedelta

# Enable Pynamodb debugging
logging.basicConfig(level=logging.DEBUG)


class User(Model):
    class Meta:
        table_name = "User"
        host = "http://localhost:8000"

    username = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    fullname = UnicodeAttribute()
    email = UnicodeAttribute()
    rooms = ListAttribute(default=list)  # List of room IDs


class Room(Model):
    class Meta:
        table_name = "Room"
        host = "http://localhost:8000"

    room_id = UnicodeAttribute(hash_key=True)
    room_name = UnicodeAttribute()
    users = ListAttribute(default=list)  # List of usernames
    admins = ListAttribute(default=list)  # List of admin usernames
    description = UnicodeAttribute(default="Add a room description")

class Message(Model):
    class Meta:
        table_name = "Message"
        host = "http://localhost:8000"

    message_id = UnicodeAttribute(hash_key=True)
    content = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    username = UnicodeAttribute()  # user who sent it
    room_id = UnicodeAttribute()


class Connection(Model):
    class Meta:
        table_name = "Connection"
        host = "http://localhost:8000"

    connection_id = UnicodeAttribute(hash_key=True)
    username = UnicodeAttribute()
    room_id = UnicodeAttribute()
    connected_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))


class UsernameStatusIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = "username-status-index"
        projection = AllProjection()
        read_capacity_units = 1
        write_capacity_units = 1

    username = UnicodeAttribute(hash_key=True)
    status = UnicodeAttribute(range_key=True)
    request_type = UnicodeAttribute()

class StatusIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = "status-index"
        projection = AllProjection()

    status = UnicodeAttribute(hash_key=True)   # <-- status as partition key
    room_id = UnicodeAttribute()
    username = UnicodeAttribute()

class MembershipRequest(Model):
    class Meta:
        table_name = "MembershipRequest"
        host = "http://localhost:8000"

    room_id = UnicodeAttribute(hash_key=True)  # Room where request applies
    username = UnicodeAttribute(range_key=True)  # User involved (either invited or requesting)
    request_type = UnicodeAttribute()  # "invite" | "join_request"
    status = UnicodeAttribute(default="pending")  # "pending" | "accepted" | "rejected"
    created_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    username_status_index = UsernameStatusIndex()
    status_index = StatusIndex()

print("Loaded Models", flush=True)
