import sys
import os

from tests.factories.base import BaseFactory
from tests.factories.models import RoomFactory, RoomMembershipFactory, UserFactory

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pytest

@pytest.fixture(autouse=True)
def bind_factories_to_db(db):
    from tests.factories.models import (
        RoomFactory, RoomMembershipFactory, UserFactory, MessageFactory,
        MembershipRequestFactory, UserMessageFactory, ReplyThreadFactory,
        UserReactionFactory, ConnectionFactory
    )
    
    factories = [
        RoomFactory, RoomMembershipFactory, UserFactory, MessageFactory,
        MembershipRequestFactory, UserMessageFactory, ReplyThreadFactory,
        UserReactionFactory, ConnectionFactory
    ]
    for factory in factories:
        factory._meta.sqlalchemy_session = db
    
    yield
    
    for factory in factories:
        factory._meta.sqlalchemy_session = None


@pytest.fixture(autouse=True)
def reset_sequences():
    RoomFactory.reset_sequence()
    RoomMembershipFactory.reset_sequence()
    UserFactory.reset_sequence()