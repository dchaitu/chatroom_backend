import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Column, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column

import sqlalchemy as sa



class Base(DeclarativeBase):
    pass

# engine = sa.create_engine("postgresql://neondb_owner:npg_2iCJBEO0MIwj@ep-shiny-mode-ad5ttg3k-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
engine = sa.create_engine("sqlite:///test.db")

association_table = Table(
    "association_table",
    Base.metadata,
    Column("username", String, ForeignKey("User.username")),
    Column("room_id", String, ForeignKey("Room.room_id"))
)

class User(Base):
    __tablename__ = "User"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String)
    fullname: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    avatar: Mapped[str] = mapped_column(String,default="😁")
    pic_url: Mapped[str | None] = mapped_column(String,nullable=True)

    # relationships
    rooms: Mapped[list["Room"]] = relationship(secondary=association_table, back_populates="users")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user")
    user_messages: Mapped[list["UserMessage"]] = relationship("UserMessage", back_populates="user")
    reactions: Mapped[list["UserReaction"]] = relationship("UserReaction", back_populates="user")
    replies: Mapped[list["ReplyThread"]] = relationship("ReplyThread", back_populates="user")
    membership_requests: Mapped[list["MembershipRequest"]] = relationship("MembershipRequest",
                                                                          back_populates="user",
                                                                          foreign_keys="[MembershipRequest.username]")

    created_membership_requests: Mapped[list["MembershipRequest"]] = relationship(
        "MembershipRequest",
        back_populates="creator",
        foreign_keys="[MembershipRequest.created_by]"
    )

    room_memberships: Mapped[list["RoomMembership"]] = relationship("RoomMembership", back_populates="user")
    # connections: Mapped[list["Connection"]] = relationship("Connection", back_populates="user")

    def __repr__(self):
        return f"User(username={self.username}, fullname={self.fullname}, email={self.email})"

class Room(Base):
    __tablename__ = "Room"

    room_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_name: Mapped[str] = mapped_column(String)
    users: Mapped[list[User]] = relationship(secondary=association_table, back_populates="rooms")
    description: Mapped[str] = mapped_column(String)

    # relationships
    membership_requests: Mapped[list["MembershipRequest"]] = relationship("MembershipRequest", back_populates="room")
    room_memberships: Mapped[list["RoomMembership"]] = relationship("RoomMembership", back_populates="room")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="room")



class Message(Base):
    __tablename__ = "Message"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    room_id: Mapped[str] = mapped_column(String, ForeignKey("Room.room_id"))
    file_url: Mapped[str] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    room: Mapped["Room"] = relationship("Room", back_populates="messages")
    replies: Mapped[list["ReplyThread"]] = relationship("ReplyThread", back_populates="message")
    user_messages: Mapped[list["UserMessage"]] = relationship("UserMessage", back_populates="message")
    reactions: Mapped[list["UserReaction"]] = relationship("UserReaction", back_populates="message")

class MembershipRequest(Base):
    __tablename__ = "MembershipRequest"


    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("Room.room_id"), nullable=False)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'invite' or 'join_request'
    status: Mapped[str] = mapped_column(String(20), default="pending")  # 'pending', 'accepted', 'rejected'
    created_by: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # relationships
    user = relationship("User", back_populates="membership_requests", foreign_keys=[username])
    creator = relationship("User", back_populates="created_membership_requests", foreign_keys=[created_by])
    room = relationship("Room", back_populates="membership_requests")


class RoomMembership(Base):
    __tablename__ = "RoomMembership"


    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("Room.room_id"), nullable=False)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_read_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    room = relationship("Room", back_populates="room_memberships")
    user = relationship("User", back_populates="room_memberships")


class UserMessage(Base):
    __tablename__ = "UserMessage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("Message.message_id"), nullable=False)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="user_messages")
    message = relationship("Message", back_populates="user_messages")


class ReplyThread(Base):
    __tablename__ = "ReplyThread"

    thread_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reply_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("Message.message_id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationships
    message = relationship("Message", back_populates="replies")
    user = relationship("User", back_populates="replies")



class UserReaction(Base):
    __tablename__ = "UserReaction"


    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("Message.message_id"), nullable=False)
    username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    message = relationship("Message", back_populates="reactions")
    user = relationship("User", back_populates="reactions")

# class Connection(Base):
#     __tablename__ = "connections"
#
#     connection_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     username: Mapped[str] = mapped_column(ForeignKey("User.username"), nullable=False)
#     room_id: Mapped[str] = mapped_column(ForeignKey("Room.room_id"), nullable=False)
#     connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
#
#     # relationships
#     user = relationship("User", back_populates="connections")
#     room = relationship("Room", back_populates="connections")

# Create all tables
def create_tables():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    create_tables()