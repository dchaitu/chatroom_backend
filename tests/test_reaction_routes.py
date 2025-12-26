from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from constants import get_current_user
from rest_api import app
from database import get_db
from models.rds_models import Base, UserReaction
from schemas import UserReactionDTO
from storages.rds_storage_implementation import RDSStorageImplementation
from tests.factories.models import UserReactionFactory, MessageFactory, UserFactory, RoomFactory
from tests.factories.dtos import ReactionDTOFactory, UserReactionDTOFactory
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
async def test_create_reaction_to_message(db, client):
    # Arrange
    user = UserFactory.build(username="test_user")
    message = MessageFactory.build()
    db.add(user)
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    db.commit()
    
    reaction_dto = ReactionDTOFactory(message_id=message.message_id)
    
    # Act
    response = client.post("/reaction/create/", json={
        "message_id": message.message_id,
        "reaction_type": reaction_dto.reaction_type
    })

    # Assert
    assert response.status_code == 201
    
    # Verify DB
    reaction = db.query(UserReaction).filter_by(message_id=message.message_id, username=user.username).first()
    assert reaction is not None
    assert reaction.reaction_type == reaction_dto.reaction_type

@pytest.mark.asyncio
async def test_get_reactions_to_messages_in_room(db, client):
    # Arrange
    room = RoomFactory.build()
    user = UserFactory.build(username="test_user")
    db.add(room)
    db.add(user)
    
    message1 = MessageFactory.build(room=room)
    message2 = MessageFactory.build(room=room)
    if message1.user: db.add(message1.user)
    if message2.user: db.add(message2.user) 
    db.add(message1)
    db.add(message2)
    
    ur1 = UserReactionFactory.build(message=message1, user=user)
    ur2 = UserReactionFactory.build(message=message2, user=user)
    db.add(ur1)
    db.add(ur2)
    
    db.commit()
    
    # Act
    response = client.get(f"/reaction/{room.room_id}/")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2

# TODO Update the testcase
@pytest.mark.asyncio
async def test_get_all_reactions(db, client):
    # Arrange
    reactions = [UserReactionFactory() for _ in range(3)]
    # dtos = [UserReactionDTOFactory(r) for r in reactions]
    dtos = [
        UserReactionDTO.model_validate(r).model_dump(mode="json")
        for r in reactions
    ]
    expected_models = [
        UserReactionDTO.model_validate(r)
        for r in reactions
    ]

    # Act
    response = client.get("/reaction/all-reactions/")
    response_models = [
        UserReactionDTO.model_validate(item)
        for item in response.json()
    ]




    # Assert
    assert response.status_code == 200
    # assert len(response.json()) >= 3
    assert response_models == expected_models

@pytest.mark.asyncio
async def test_storage_create_reaction(db):
    # Arrange
    user = UserFactory.build()
    message = MessageFactory.build()
    db.add(user)
    if message.room: db.add(message.room)
    if message.user: db.add(message.user)
    db.add(message)
    db.commit()
    
    reaction_dto = ReactionDTOFactory(message_id=message.message_id)
    storage = RDSStorageImplementation(db)
    
    # Act
    reaction = await storage.create_reaction_to_message(reaction_dto, user.username)
    
    # Assert
    assert reaction.message_id == message.message_id
    assert reaction.reaction_type == reaction_dto.reaction_type
