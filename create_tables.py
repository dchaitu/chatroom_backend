import os
from models import User, Room, Message, Connection

def create_dynamodb_tables():
    print("User table exists: ",User.exists())
    print("Room table exists: ",Room.exists())
    table_names = [User, Room, Message, Connection]


    for table in table_names:
        if not table.exists():
            print(f"Creating {table.Meta.table_name} table...")
            table.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
            print(f"{table.Meta.table_name} table created successfully.")
        else:
            print(f"{table.Meta.table_name} table already exists.")


if __name__ == "__main__":
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    print("ENVIRONMENT in create_tables.py", ENVIRONMENT)
    create_dynamodb_tables()