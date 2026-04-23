from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(20), primary_key=True)
    username = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    password = Column(Text, nullable=False)
    role = Column(Text, nullable=False) # 'Client' or 'Admin'
    avatar_url = Column(String(500))
    status = Column(String(20), default='offline') # 'online', 'offline', 'away'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True))

class Conversation(Base):
    __tablename__ = "conversations"

    conver_id = Column(Integer, primary_key=True, autoincrement=True)
    user_a_id = Column(String(20), ForeignKey("users.user_id"))
    user_b_id = Column(String(20), ForeignKey("users.user_id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    conver_id = Column(Integer, ForeignKey("conversations.conver_id"))
    sender_id = Column(String(20), ForeignKey("users.user_id"))
    reply_to_id = Column(Integer, ForeignKey("messages.message_id"), nullable=True)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True))