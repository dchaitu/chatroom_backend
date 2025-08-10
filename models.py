from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, ListAttribute
from datetime import datetime, timezone


class User(Model):
    class Meta:
        table_name = "User"
        region = "us-east-1"  # change as needed

    username = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    fullname = UnicodeAttribute()
    email = UnicodeAttribute()
    rooms = ListAttribute(default=list)  # List of room IDs


class Room(Model):
    class Meta:
        table_name = "Room"
        region = "us-east-1"

    room_id = UnicodeAttribute(hash_key=True)
    room_name = UnicodeAttribute()
    users = ListAttribute(default=list)  # List of usernames


class Message(Model):
    class Meta:
        table_name = "Message"
        region = "us-east-1"

    message_id = UnicodeAttribute(hash_key=True)
    content = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    username = UnicodeAttribute()   # user who sent it
    room_id = UnicodeAttribute()


class Connection(Model):
    class Meta:
        table_name = "Connection"
        region = "us-east-1"

    connection_id = UnicodeAttribute(hash_key=True)
    username = UnicodeAttribute()
    room_id = UnicodeAttribute()
    connected_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))

print("Loaded Models", flush=True)