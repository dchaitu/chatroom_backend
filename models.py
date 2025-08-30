import logging
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, ListAttribute
from datetime import datetime, timezone


# Enable Pynamodb debugging
logging.basicConfig(level=logging.DEBUG)



class User(Model):
    class Meta:
        table_name = "User"
        host = 'http://localhost:8000'

    username = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    fullname = UnicodeAttribute()
    email = UnicodeAttribute()
    rooms = ListAttribute(default=list)  # List of room IDs


class Room(Model):
    class Meta:
        table_name = "Room"
        host = 'http://localhost:8000'

    room_id = UnicodeAttribute(hash_key=True)
    room_name = UnicodeAttribute()
    users = ListAttribute(default=list)  # List of usernames
    admins = ListAttribute(default=list)  # List of admin usernames
    description = UnicodeAttribute(default="Add a room description")

class Message(Model):
    class Meta:
        table_name = "Message"
        host = 'http://localhost:8000'


    message_id = UnicodeAttribute(hash_key=True)
    content = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    username = UnicodeAttribute()   # user who sent it
    room_id = UnicodeAttribute()


class Connection(Model):
    class Meta:
        table_name = "Connection"
        host = 'http://localhost:8000'


    connection_id = UnicodeAttribute(hash_key=True)
    username = UnicodeAttribute()
    room_id = UnicodeAttribute()
    connected_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))

print("Loaded Models", flush=True)