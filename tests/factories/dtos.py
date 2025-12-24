import uuid

import factory

from schemas import RoomSchema, RoomDTO


class RoomSchemaFactory(factory.Factory):
    class Meta:
        model = RoomSchema

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Faker("company")
    description = factory.Faker("sentence")
    users = factory.List(
        [
            factory.Faker("username_1"),
            factory.Faker("username_2"),
        ]
    )

class RoomDTOFactory(factory.Factory):
    class Meta:
        model = RoomDTO

    room_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    room_name = factory.Faker("company")
    description = factory.Faker("sentence")