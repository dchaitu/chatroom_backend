from datetime import datetime, UTC

from sqlalchemy import ForeignKey, String, Column, DateTime
from sqlalchemy.orm import declarative_base,  relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    username = Column(String, primary_key=True)
    password = Column(String)
    fullname = Column(String)
    email = Column(String)
    rooms = relationship("Room", secondary="table_room", back_populates="users")
    messages = relationship("Message", back_populates="sender")
    connections = relationship("Connection", back_populates="user")

class Room(Base):
    __tablename__ = "room"
    room_id = Column(String, primary_key=True)
    room_name = Column(String)
    users = relationship("User", secondary="table_room", back_populates="rooms")
    messages = relationship("Message", back_populates="room")
    connections = relationship("Connection", back_populates="room")


class TableRoom(Base):
    __tablename__ = "table_room"
    user_id = Column(ForeignKey("user.username"), primary_key=True)
    room_id = Column(ForeignKey("room.room_id"), primary_key=True)


class Message(Base):
    __tablename__ = "message"
    message_id = Column(String, primary_key=True)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.now(UTC))
    username = Column(ForeignKey("user.username"))
    room_id = Column(String,ForeignKey("room.room_id"))
    sender = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")


class Connection(Base):
    __tablename__ = "connection"
    connection_id = Column(String, primary_key=True)
    username = Column(ForeignKey("user.username"))
    room_id = Column(ForeignKey("room.room_id"))
    connected_at = Column(DateTime, default=datetime.now(UTC))
    user = relationship("User", back_populates="connections")
    room = relationship("Room", back_populates="connections")