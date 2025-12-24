import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from rest_api import app
from database import get_db
from storages.rds_storage_implementation import RDSStorageImplementation
from schemas import MakeRoomAdmin
from models.rds_models import Base, Room, RoomMembership
from tests.factories.models import RoomFactory, RoomMembershipFactory

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)

def override_get_db_local():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()



@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[get_db] = override_get_db_local
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {}

@pytest.fixture
def room_factory(db):
    class _RoomFactory(RoomFactory):
        class Meta:
            sqlalchemy_session = db
    return _RoomFactory


@pytest.fixture
def room_membership_factory(db):
    class _RoomMembershipFactory(RoomMembershipFactory):
        class Meta:
            sqlalchemy_session = db
    return _RoomMembershipFactory


@pytest.mark.asyncio
async def test_create_room_admin(db, room_factory, room_membership_factory):

    # Arrange
    room = room_factory(
        room_id="test_room_id",
        room_name="test_room_name",
        description="test_room_description"
    )

    room_membership_factory(
        room=room,
        username="test_user",
        is_admin=False
    )


    # Act
    storage = RDSStorageImplementation()
    response = await storage.create_room_admin(MakeRoomAdmin(room_id="test_room_id", username="test_user"), db=db)

    # Assert
    assert response.room_id == room.room_id
    assert response.room_name == room.room_name
    assert response.description == room.description