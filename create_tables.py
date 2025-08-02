from models import User, Room, Message, Connection

def create_dynamodb_tables():
    # Create User table
    if not User.exists():
        print("Creating User table...")
        User.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
        print("User table created successfully.")
    else:
        print("User table already exists.")

    # Create Room table
    if not Room.exists():
        print("Creating Room table...")
        Room.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
        print("Room table created successfully.")
    else:
        print("Room table already exists.")

    # Create Message table
    if not Message.exists():
        print("Creating Message table...")
        Message.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
        print("Message table created successfully.")
    else:
        print("Message table already exists.")

    # Create Connection table with GSI
    if not Connection.exists():
        print("Creating Connection table...")
        Connection.create_table(
            read_capacity_units=5,
            write_capacity_units=5,
            wait=True
        )
        print("Connection table created successfully.")
    else:
        print("Connection table already exists.")

if __name__ == "__main__":
    create_dynamodb_tables()