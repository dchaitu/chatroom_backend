import logging
import os

import boto3
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute, ListAttribute
from datetime import datetime, timezone


# Enable Pynamodb debugging
logging.basicConfig(level=logging.DEBUG)

# Environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DYNAMODB_HOST = os.getenv('DYNAMODB_HOST', 'http://localhost:8000')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Set dummy AWS credentials
session = boto3.Session(aws_access_key_id='fake',
    aws_secret_access_key='fake',
    region_name=AWS_REGION)
aws_credentials = session.get_credentials()
aws_access_key_id = aws_credentials.access_key
aws_secret_access_key = aws_credentials.secret_key


class BaseModel(Model):
    class Meta:
        region = AWS_REGION
        host = 'http://localhost:8000'
        aws_access_key_id = aws_access_key_id
        aws_secret_access_key = aws_secret_access_key

        if host:
            print(f"Models configured for LOCAL DynamoDB at {host}")
        else:
            print("Models configured for AWS DynamoDB")
        print("ENVIRONMENT", ENVIRONMENT)
        # Only set host for local development
        if ENVIRONMENT in ['development', 'testing']:
            host = DYNAMODB_HOST
            print(f"Models configured for LOCAL DynamoDB at {DYNAMODB_HOST}")

        else:
            print("Models configured for AWS DynamoDB")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"Model {self.__class__.__name__} configured for "
              f"{'LOCAL DynamoDB at ' + DYNAMODB_HOST if self.Meta.host else 'AWS DynamoDB'}")
        print(f"ENVIRONMENT: {ENVIRONMENT}")
        print(f"AWS Profile: {session.profile_name}, Access Key: {self.Meta.aws_access_key_id}")


class User(BaseModel):
    class Meta:
        table_name = "User"
        host = 'http://localhost:8000'

    username = UnicodeAttribute(hash_key=True)
    password = UnicodeAttribute()
    fullname = UnicodeAttribute()
    email = UnicodeAttribute()
    rooms = ListAttribute(default=list)  # List of room IDs


class Room(BaseModel):
    class Meta:
        table_name = "Room"
        host = 'http://localhost:8000'

    room_id = UnicodeAttribute(hash_key=True)
    room_name = UnicodeAttribute()
    users = ListAttribute(default=list)  # List of usernames


class Message(BaseModel):
    class Meta:
        table_name = "Message"
        host = 'http://localhost:8000'


    message_id = UnicodeAttribute(hash_key=True)
    content = UnicodeAttribute()
    timestamp = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))
    username = UnicodeAttribute()   # user who sent it
    room_id = UnicodeAttribute()


class Connection(BaseModel):
    class Meta:
        table_name = "Connection"
        host = 'http://localhost:8000'


    connection_id = UnicodeAttribute(hash_key=True)
    username = UnicodeAttribute()
    room_id = UnicodeAttribute()
    connected_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))

print("Loaded Models", flush=True)