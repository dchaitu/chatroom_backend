from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from constants import get_current_user
from rest_api import app
from database import get_db
from models.rds_models import Base, ReplyThread
from storages.rds_storage_implementation import RDSStorageImplementation
from tests.factories.models import ReplyThreadFactory, MessageFactory, UserFactory
from tests.factories.dtos import ReplyMessageDTOFactory
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
async def test_create_reply_to_message(db, client):
    # Arrange
    user = UserFactory.build(username="test_user")
    message = MessageFactory.build()
    db.add(user)
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    db.commit()
    
    reply_dto = ReplyMessageDTOFactory(message_id=message.message_id)
    
    # Act
    response = client.post("/reply/create/", json={
        "message_id": reply_dto.message_id,
        "content": reply_dto.content
    })

    # Assert
    assert response.status_code == 201
    
    # Verify DB
    reply = db.query(ReplyThread).filter_by(message_id=message.message_id, username=user.username).first()
    assert reply is not None
    assert reply.content == reply_dto.content

@pytest.mark.asyncio
async def test_get_message_reply_count(db, client):
    # Arrange
    message = MessageFactory.build()
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    
    replies = ReplyThreadFactory.build_batch(3, message=message)
    for r in replies:
        if r.user: db.add(r.user)
        db.add(r)
    db.commit()
    
    # Act
    response = client.get(f"/reply/{message.message_id}/count/")

    # Assert
    assert response.status_code == 200
    assert response.json() == {message.message_id: 3}

@pytest.mark.asyncio
async def test_show_replies_for_messages(db, client):
    # Arrange
    message = MessageFactory.build()
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    
    replies = ReplyThreadFactory.build_batch(2, message=message)
    for r in replies:
        if r.user: db.add(r.user)
        db.add(r)
    db.commit()
    
    # Act
    response = client.get(f"/reply/show-replies-for/{message.message_id}/")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_show_all_replies(db, client):
    # Arrange
    replies = ReplyThreadFactory.build_batch(3)
    for r in replies:
        if r.message:
            if r.message.room: db.add(r.message.room)
            if r.message.user: db.add(r.message.user)
            db.add(r.message)
        if r.user: db.add(r.user)
        db.add(r)
    db.commit()
    
    # Act
    response = client.get("/reply/all-replies/")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) >= 3

@pytest.mark.asyncio
async def test_storage_create_reply(db):
    # Arrange
    user = UserFactory.build()
    message = MessageFactory.build()
    db.add(user)
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    db.commit()
    
    reply_dto = ReplyMessageDTOFactory(message_id=message.message_id)
    storage = RDSStorageImplementation(db)
    
    # Act
    reply = await storage.create_reply_to_message(reply_dto, user.username)
    
    # Assert
    assert reply.message_id == message.message_id
    assert reply.content == reply_dto.content
