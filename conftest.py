import sys
import os

from factory.base import BaseFactory

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pytest

@pytest.fixture(autouse=True)
def bind_factories_to_db(db):
    BaseFactory._meta.sqlalchemy_session = db
    yield
    BaseFactory._meta.sqlalchemy_session = None