import boto3
import os
from botocore.exceptions import ClientError


# # Get environment
# ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
#
# # Configure DynamoDB client based on environment
# if ENVIRONMENT == 'development':
#     dynamodb = boto3.resource(
#         'dynamodb',
#         region_name='us-east-1',
#         endpoint_url='http://localhost:8000',
#         aws_access_key_id='TEST',
#         aws_secret_access_key='TEST'
#     )
# else:
#     dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
#
# table_names = {
#     'users': os.environ.get('DYNAMODB_USERS_TABLE', 'Users'),
#     'rooms': os.environ.get('DYNAMODB_ROOMS_TABLE', 'Rooms'),
#     'messages': os.environ.get('DYNAMODB_MESSAGES_TABLE', 'Messages'),
#     'connections': os.environ.get('DYNAMODB_CONNECTIONS_TABLE', 'Connections')
# }
#
# def get_table(table_name):
#     return dynamodb.Table(table_names[table_name])
#
# def get_db():
#     return {
#         'users': get_table('users'),
#         'rooms': get_table('rooms'),
#         'messages': get_table('messages'),
#         'connections': get_table('connections')
#     }

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB_USER = os.getenv("DB_USER","neondb_owner")
# DB_PASSWORD = os.getenv("DB_PASSWORD","npg_Yvh8Rm2yDuWG")
# DB_HOST = os.getenv("DB_HOST","ep-bitter-flower-a4cbrm5z-pooler.us-east-1.aws.neon.tech")
# DB_PORT = os.getenv("DB_PORT", "5432")
# DB_NAME = os.getenv("DB_NAME","chatroomdb")

# DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# print("DATABASE_URL ", DATABASE_URL)
# engine = create_engine(DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()