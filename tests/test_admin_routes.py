from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from constants import get_current_user
from rest_api import app
from database import get_db
from storages.rds_storage_implementation import RDSStorageImplementation
from schemas import MakeRoomAdmin
from models.rds_models import Base, Room, RoomMembership, MembershipRequest
from tests.factories.dtos import MembershipRequestSchemaFactory, UserActionDTOFactory, MakeRoomAdminFactory
from tests.factories.models import RoomFactory, RoomMembershipFactory, MembershipRequestFactory, UserFactory

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
    try:
        yield session
    finally:
        session.rollback()
        session.close()



@pytest.fixture(scope="function")
def client():
    def override_get_current_user():
        return "test_user"
    app.dependency_overrides[get_db] = override_get_db_local
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()



@pytest.mark.asyncio
async def test_create_room_admin(db):

    # Arrange
    room = RoomFactory(
        room_id="test_room_1",
        room_name="test_room_name",
        description="test_room_description"
    )

    RoomMembershipFactory(
        room=room,
        username="test_user",
        is_admin=False
    )

    # Act
    storage = RDSStorageImplementation(db)
    response = await storage.create_room_admin(MakeRoomAdmin(room_id="test_room_1", username="test_user"))

    # Assert
    assert response.room_id == room.room_id
    assert response.room_name == room.room_name
    assert response.description == room.description
    member = db.query(RoomMembership).filter_by(
        room_id=room.room_id,
        username="test_user"
    ).one()
    assert member.is_admin is True
    assert member.id is not None
    assert isinstance(member.id, int)

def make_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

@freeze_time("2025-12-24T10:10:10Z")
@pytest.mark.asyncio
async def test_get_pending_requests(db):
    # Arrange
    request_type = "join_request"
    username="chaitu"
    room = RoomFactory(
        room_id="test_room_id",
        room_name="test_room_name",
        description="test_room_description"
    )
    UserFactory(username=username)

    RoomMembershipFactory(
        room=room,
        username=username,
        is_admin=True
    )
    request = MembershipRequestFactory(room=room, username=username, request_type=request_type, status="pending")

    expected_response = MembershipRequestSchemaFactory(
        room_id=room.room_id,
        username=username,
        request_type=request_type,
        status="pending",
        created_by=request.created_by,
        created_at=datetime.now(timezone.utc)
    )

    # Act
    storage = RDSStorageImplementation(db)
    response = await storage.get_pending_requests(request_type=request_type, username=username)

    # Assert
    assert response[0].room_id == expected_response.room_id
    assert response[0].username == expected_response.username
    assert response[0].request_type == expected_response.request_type
    assert response[0].status == expected_response.status
    assert response[0].created_by == expected_response.created_by
    assert make_utc(response[0].created_at) == make_utc(expected_response.created_at)


@pytest.mark.asyncio
async def test_admin_respond_to_room_membership_request(db):
    # Arrange
    room_id = "test_room_2"
    username = "test_user_2"
    admin_username = "admin_user"
    created_by = admin_username
    user_action = UserActionDTOFactory(
        requested_user=username,
        action="accept"
    )

    RoomFactory(room_id=room_id)
    UserFactory(username=admin_username, email="admin@example.com")
    UserFactory(username=username)

    MembershipRequestFactory(
        room_id=room_id,
        username=username,
        request_type="join_request",
        status="pending",
        created_by=username
    )
    RoomMembershipFactory(
        room_id=room_id,
        username=admin_username,
        is_admin=True
    )
    expected_response = {"message": f"Membership request {user_action.action} for user {user_action.requested_user} in room {room_id}"}

    # Act
    storage = RDSStorageImplementation(db)
    response = await storage.admin_respond_to_room_membership_request(
        user_action=user_action, room_id=room_id,current_user=admin_username)

    # Assert
    assert response == expected_response


@pytest.mark.asyncio
async def test_admin_respond_to_room_membership_request_not_found(db,client):
    # Arrange
    room = RoomFactory()
    user = UserFactory(username="test_2", email="test2@example.com")
    membership_request = MembershipRequestFactory(
        username=user.username,
        room_id=room.room_id,
        status="accepted",
        request_type="join_request",
        created_by=user.username)
    room_id = membership_request.room_id

    # Act
    response = client.post(f"/admin/request/{room.room_id}/respond/",
                           json={
                               "requested_user": user.username,  # This user doesn't have a request
                               "action": "accept"
                           }
                           )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": f"Membership request with room_id={room_id} not found"}


@pytest.mark.asyncio
async def test_create_room_admin_response_user_not_found(db, client):
    # Arrange
    room_id = "1"
    room_admin = MakeRoomAdminFactory(room_id=room_id)
    UserFactory(username="test_user", email="test@example.com")  # This is the user that will be authenticated
    non_existent_user = "non_existent_user"
    RoomFactory(room_id=room_id)
    RoomMembershipFactory(
        room_id=room_id,
        username=room_admin.username,
        is_admin=True
    )

    # Act
    response = client.post(f"/admin/create/", json={
        "requested_user":non_existent_user,
        "action":"accept"
    })

    # Assert
    print("Response", response)
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found in room"}


@pytest.mark.asyncio
async def test_create_room_admin_response_user_not_found(db, client):
    # Arrange
    room_id = "1"
    room_admin = MakeRoomAdminFactory(room_id=room_id)
    UserFactory(username="test_user", email="test@example.com")  # This is the user that will be authenticated
    non_existent_user = "non_existent_user"
    RoomFactory(room_id=room_id)
    RoomMembershipFactory(
        room_id=room_id,
        username=room_admin.username,
        is_admin=True
    )

    # Act
    response = client.post(f"/admin/request/{room_id}/respond/", json={
        "requested_user":non_existent_user,
        "action":"accept"
    })

    # Assert
    print("Response", response)
    assert response.status_code == 404
    assert response.json() == {"detail": f"Membership request with room_id={room_id} not found"}


@pytest.mark.asyncio
async def test_get_pending_requests_user_not_admin_return_empty_list(db, client):
    # Arrange
    username = "test_user"
    request_type = "join_request"

    room = RoomFactory(room_id="room_1")

    MembershipRequestFactory(
        room=room,
        username=username,
        request_type=request_type,
        status="pending",
        created_by=username
    )

    RoomMembershipFactory(
        room=room,
        username=username,
        is_admin=False,
    )

    # Act
    response = client.get(f"/admin/pending-requests/?request_type={request_type}")

    # Assert
    assert response.status_code == 200
    assert response.json() == []



