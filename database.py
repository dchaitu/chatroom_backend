import boto3
import os
from botocore.exceptions import ClientError

from models import User, Room, Message, Connection

dynamodb = boto3.resource(
    "dynamodb", region_name="us-east-1"
)  # Adjust region as needed
table_names = {
    "users": os.environ.get("DYNAMODB_USERS_TABLE", "Users"),
    "rooms": os.environ.get("DYNAMODB_ROOMS_TABLE", "Rooms"),
    "messages": os.environ.get("DYNAMODB_MESSAGES_TABLE", "Messages"),
    "connections": os.environ.get("DYNAMODB_CONNECTIONS_TABLE", "Connections"),
}


def get_table(table_name):
    return dynamodb.Table(table_names[table_name])


def get_db():
    return {
        "users": User,
        "rooms": Room,
        "messages": Message,
        "connections": Connection,
    }
