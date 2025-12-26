import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

from freezegun import freeze_time

from schemas import MessageSchema
from tests.factories.dtos import MessageInfoDTOFactory

sys.modules["boto3"] = MagicMock()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from constants import get_current_user
from rest_api import app
from database import get_db
from models.rds_models import Base, Message
from storages.rds_storage_implementation import RDSStorageImplementation
from tests.factories.models import MessageFactory, RoomFactory, UserFactory, UserMessageFactory
from tests.factories.base import BaseFactory

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
    BaseFactory._meta.sqlalchemy_session = session
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
async def test_get_messages(db, client):
    # Arrange
    room = RoomFactory.build()
    user = UserFactory.build(username="test_user")

    messages = [MessageFactory( room=room, user=user),
                MessageFactory( room=room, user=user),
                MessageFactory( room=room, user=user)]
    
    # Act
    response = client.get(f"/messages/{room.room_id}")

    # Assert
    assert response.status_code == 200
    assert response.json() == [MessageSchema.model_validate(m).model_dump(mode="json") for m in messages]


@pytest.mark.asyncio
async def test_send_message(db, client):
    # Arrange
    room = RoomFactory()
    user = UserFactory(username="test_user")
    content = "Hello World"
    
    # Act
    response = client.post("/messages/send/", data={"content": content, "room_id": room.room_id})

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data['content'] == content
    assert data['room_id'] == room.room_id
    
    msg = db.query(Message).filter_by(content=content).first()
    assert msg is not None

@freeze_time("2025-12-24T10:10:10Z")
@pytest.mark.asyncio
async def test_get_all_messages(db, client):
    # Arrange
    room = RoomFactory(room_id=1)
    messages = [MessageFactory(room=room),
                MessageFactory(room=room),
                ]
    # Act
    response = client.get("/messages/all/")

    # Assert
    assert response.status_code == 200
    assert response.json() == [MessageSchema.model_validate(m).model_dump(mode="json") for m in messages]

@freeze_time("2025-12-24T10:10:10Z")
@pytest.mark.asyncio
async def test_get_message_last_seen_info(db, client):
    # Arrange
    room = RoomFactory()
    user = UserFactory(username="test_user")
    messages = [MessageFactory(room=room, user=user), MessageFactory(room=room, user=user)]
    user_messages = [UserMessageFactory(message=msg, user=user,read_at=datetime.now(timezone.utc)) for msg in messages]
    dtos = [MessageInfoDTOFactory(message_id=m.message_id, username=m.username,read_at=m.read_at) for m in user_messages]

    # Act
    response = client.get(f"/messages/info/{room.room_id}")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json() == [dto.model_dump(mode="json") for dto in dtos]

@pytest.mark.asyncio
async def test_storage_get_messages(db):
    # Arrange
    room = RoomFactory()
    db.add(room)
    messages = [
                    MessageFactory(room=room),
                    MessageFactory(room=room),
                    MessageFactory(room=room)
                ]

    storage = RDSStorageImplementation(db)
    
    # Act
    result_messages = await storage.get_messages(room.room_id)
    
    # Assert
    assert len(result_messages) == 3

@pytest.mark.asyncio
async def test_storage_send_message(db):
    # Arrange
    room = RoomFactory()
    user = UserFactory()
    db.add(room)
    db.add(user)
    db.commit()
    
    content = "Storage Message"
    storage = RDSStorageImplementation(db)
    
    # Act
    message_dict = await storage.send_message(content=content, room_id=room.room_id, file=None, username=user.username)
    
    # Assert
    assert message_dict['content'] == content
    assert message_dict['room_id'] == room.room_id
