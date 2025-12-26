import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from constants import get_current_user
from rest_api import app
from database import get_db
from models.rds_models import Base, Room, RoomMembership, MembershipRequest
from storages.rds_storage_implementation import RDSStorageImplementation
from tests.factories.models import RoomFactory, RoomMembershipFactory, UserFactory, MembershipRequestFactory
from tests.factories.dtos import RoomCreateFactory

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
    # BaseFactory._meta.sqlalchemy_session = session
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_current_user():
        return "test_user"
    app.dependency_overrides[get_db] = override_get_db_local
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_room(db, client):
    # Arrange
    user = UserFactory.build(username="test_user")
    db.add(user)
    db.commit()
    
    room_data = RoomCreateFactory() # DTO factory, simple object
    
    # Act
    payload = {
        "room_id": room_data.room_id,
        "room_name": room_data.room_name,
        "description": room_data.description
    }
    response = client.post("/room/create/", json=payload)

    # Assert
    assert response.status_code == 201
    assert "message" in response.json()
    
    room = db.query(Room).filter_by(room_id=room_data.room_id).first()
    assert room is not None
    membership = db.query(RoomMembership).filter_by(room_id=room_data.room_id, username=user.username).first()
    assert membership is not None
    assert membership.is_admin is True



@pytest.mark.asyncio
async def test_user_leave_room(db, client):
    # Arrange
    user = UserFactory(username="test_user")
    room = RoomFactory()
    user.rooms.append(room)
    
    membership = RoomMembershipFactory.build(room_id=room.room_id, username=user.username)
    db.add(membership)
    db.commit()
    
    # Act
    response = client.post(f"/room/leave/?room_id={room.room_id}")

    # Assert
    assert response.status_code == 200
    
    assert room not in user.rooms

@pytest.mark.asyncio
async def test_user_request_join_room(db, client):
    # Arrange
    user = UserFactory.build(username="test_user")
    room = RoomFactory.build()

    
    # Act
    response = client.post(f"/room/{room.room_id}/join/") 
    
    # Assert
    assert response.status_code == 200
    
    # Check request created
    req = db.query(MembershipRequest).filter_by(room_id=room.room_id, username=user.username).first()
    assert req is not None
    assert req.status == 'pending'

@pytest.mark.asyncio
async def test_get_user_rooms(db, client):
    # Arrange
    user = UserFactory.build(username="test_user")
    room1 = RoomFactory.build()
    room2 = RoomFactory.build()
    db.add(user)
    db.add(room1)
    db.add(room2)
    
    # add to user.rooms relationship used by get_user_rooms
    user.rooms.append(room1)
    user.rooms.append(room2)
    db.commit()
    
    # Act
    response = client.get("/room/user/")
    
    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_get_room_details(db, client):
    # Arrange
    room = RoomFactory.build()
    db.add(room)
    db.commit()
    
    # Act
    response = client.get(f"/room/{room.room_id}")
    
    # Assert
    assert response.status_code == 200
    assert response.json()['room_id'] == room.room_id

@pytest.mark.asyncio
async def test_storage_create_room(db):
    # Arrange
    user = UserFactory()

    
    room_create = RoomCreateFactory()
    storage = RDSStorageImplementation(db)
    
    # Act
    result = await storage.create_room(room_create, user.username)
    
    # Assert
    assert "message" in result
    
    room = db.query(Room).filter_by(room_id=room_create.room_id).first()
    assert room is not None
