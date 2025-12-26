import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from constants import get_current_user
from schemas import MembershipRequestSchema
from tests.factories.models import RoomFactory, UserFactory, MembershipRequestFactory
from rest_api import app
from database import get_db
from models.rds_models import Base
from sqlalchemy.pool import StaticPool
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
async def test_get_all_invitees_and_join_requests(db, client):
    # Arrange
    room = RoomFactory()
    user = UserFactory()
    membership = MembershipRequestFactory(room_id=room.room_id, username=user.username)
    expected_response = [MembershipRequestSchema.model_validate(membership).model_dump(mode="json")]

    # Act
    response = client.get(f"/requests/all/")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_response