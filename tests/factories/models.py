import factory
from factory.alchemy import SQLAlchemyModelFactory

from models.rds_models import User, Room, RoomMembership


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    password = factory.Faker("password")
    fullname = factory.Faker("name")
    email = factory.Faker("email")
    avatar = factory.Faker("😁")
    pic_url = factory.Faker("url")


class RoomFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Room
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    room_id = factory.Faker("uuid4")
    room_name = factory.Faker("company")
    description = factory.Faker("text")



class RoomMembershipFactory(SQLAlchemyModelFactory):
    class Meta:
        model = RoomMembership
        sqlalchemy_session = None

    room = factory.SubFactory(RoomFactory)
    username = factory.Faker("username_1")