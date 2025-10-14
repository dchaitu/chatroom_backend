from sqlalchemy import select
from sqlalchemy.orm import Session

from models.rds_models import User, Room, engine, RoomMembership

# user = User(username="chaitu",
#             password="chaitu",fullname="Chaitanya Bharat Dokara",
#             email="chaitanyadokara@gmail.com",
#             rooms=[],
#             pic_url="https://chaitanya-website-portfolio.s3.eu-north-1.amazonaws.com/chaitu_pic.jpg")
#
# # user.save()
#
# print("User created successfully: ", user.username)
# user1 = User(username="admin",
#             password="admin",fullname="Administrator",
#             email="admin@admin.com",
#             rooms=[],
#             )
#
# # user1.save()
# print("User created successfully: ", user.username)
#
#
#
# room = Room(room_id="1", room_name="General", users=[user,user1], description="General Chat Room")
# # room.users.extend([user,user1])
# room2 = Room(room_id="2", room_name="Test", description="Testing Room")
# room3 = Room(room_id="3", room_name="Admin Testing", description="Testing others")

room_membership = RoomMembership(room_id="2", username="chaitu", is_admin=True)
room_membership1 = RoomMembership(room_id="3", username="admin", is_admin=True)

# room2.users.extend([user])
# room3.users.extend([user1])

# # room.save()
#
# print("Room created successfully ", room.room_name)

with Session(engine) as session:
    # session.add(user)
    # session.add(user1)
    # session.add(room)
    # session.add(room2)
    # session.add(room3)
    # session.add(room_membership)
    # session.add(room_membership1)
    # session.commit()
    # user = session.execute(select(User).where(User.username=="chaitu"))
    # results = session.execute(select(Room).where(Room.users.any(user))).scalars().all()
    # room2 = session.get(Room, "2")
    # room3 = session.get(Room, "3")
    user = session.get(User, "chaitu")
    # user1 = session.get(User, "admin")
    # room2.users.extend([user])
    # room3.users.extend([user1])
    # session.commit()
    for room in user.rooms:
        print(room.room_name)

    rooms = session.execute(select(Room)).scalars().all()
    print([(room.room_name, room.users) for room in rooms])
