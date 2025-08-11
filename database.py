import boto3
import os
from botocore.exceptions import ClientError

# Get environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Configure DynamoDB client based on environment
if ENVIRONMENT == 'development':
    dynamodb = boto3.resource(
        'dynamodb',
        region_name='us-east-1',
        endpoint_url='http://localhost:8000',
        aws_access_key_id='TEST',
        aws_secret_access_key='TEST'
    )
else:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

table_names = {
    'users': os.environ.get('DYNAMODB_USERS_TABLE', 'Users'),
    'rooms': os.environ.get('DYNAMODB_ROOMS_TABLE', 'Rooms'),
    'messages': os.environ.get('DYNAMODB_MESSAGES_TABLE', 'Messages'),
    'connections': os.environ.get('DYNAMODB_CONNECTIONS_TABLE', 'Connections')
}

def get_table(table_name):
    return dynamodb.Table(table_names[table_name])

def get_db():
    return {
        'users': get_table('users'),
        'rooms': get_table('rooms'),
        'messages': get_table('messages'),
        'connections': get_table('connections')
    }