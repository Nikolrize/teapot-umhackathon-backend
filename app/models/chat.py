from sqlalchemy import (
    Column, Integer, String, Text,
    Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.db_connection import Base


# User Table
class User(Base):
    __tablename__ = "users"

    user_id      = Column(String(20), primary_key=True)
    username     = Column(String(50),  unique=True, nullable=False, index=True)
    email        = Column(String(255), unique=True, nullable=True)
    avatar_url   = Column(String(500), nullable=True)
    status       = Column(String(20),  default="offline")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)


# Conversation Table
class Conversation(Base):
    __tablename__ = "conversations"

    conver_id    = Column(Integer, primary_key=True)
    user_a_id    = Column(String(20), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    user_b_id    = Column(String(20), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    user_a       = relationship("User", foreign_keys=[user_a_id])
    user_b       = relationship("User", foreign_keys=[user_b_id])
    messages     = relationship("Message", back_populates="conversation",
                   cascade="all, delete", order_by="Message.created_at")

# Message Table
class Message(Base):
    __tablename__ = "messages"

    message_id      = Column(Integer, primary_key=True)
    conver_id       = Column(Integer, ForeignKey("conversations.conver_id", ondelete="CASCADE"), nullable=False)
    sender_id       = Column(String(20), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    reply_to_id     = Column(Integer, ForeignKey("messages.message_id", ondelete="SET NULL"), nullable=True)
    content         = Column(Text, nullable=False)
    is_deleted      = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    conversation    = relationship("Conversation", back_populates="messages")
    sender          = relationship("User")
    reply_to        = relationship("Message", remote_side="Message.message_id")

# Read Receipt Table
class ReadReceipt(Base):
    __tablename__ = "read_receipts"

    conver_id    = Column(Integer, ForeignKey("conversations.conver_id", ondelete="CASCADE"), primary_key=True)
    user_id      = Column(String(20), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    last_read_at = Column(DateTime(timezone=True), server_default=func.now())