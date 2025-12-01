import os
from models.rds_models import User, Room, Message, Connection, MembershipRequest, RoomMembership, UserMessage, ReplyThread, \
    UserReaction

# Invite, JoinRequest
table_names = [User, Room, Message, Connection]
def create_dynamodb_tables(table_names):

    for table in table_names:
        if not table.exists():
            print(f"Creating {table.Meta.table_name} table...")
            table.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
            print(f"{table.Meta.table_name} table created successfully.")
        else:
            print(f"{table.Meta.table_name} table already exists.")

def create_all_messages():
    messages = list(Message.scan())
    for msg in messages:
        room_users = Room.get(msg.room_id).users
        for user in room_users:
            user_message = UserMessage(
                message_id=msg.message_id,
                username=user
            )
            user_message.save()
        print("UserMessage with message_id: ", msg.message_id, "created successfully.")

    print("All messages created successfully.")


if __name__ == "__main__":
    # ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    # print("ENVIRONMENT in create_tables.py", ENVIRONMENT)
    # if Invite.exists():
    #     Invite.delete_table()
    #     print("Invite table deleted successfully.")
    # if not MembershipRequest.exists():
    #     MembershipRequest.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
    #     print("MembershipRequest table created successfully.")
    # create_dynamodb_tables()
    # room_id = "1"
    # username = "chaitu"
    # room = Room.get(room_id)
    # if username in room.users:
    #     room.users.remove(username)  # remove from list
    #     room.save()
    # if not RoomMembership.exists():
    #     RoomMembership.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
    #     print("RoomMembership table created successfully.")
    # if not UserMessage.exists():
    #     UserMessage.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)
    #     print("UserMessage table created successfully.")

    # create_all_messages()
    create_dynamodb_tables([UserReaction])





