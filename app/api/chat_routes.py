from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session 
from app.db_connection import get_db
from app.services.chat_manager import chat_manager
from app.services import chat_service as svc
from app.models.chat import Conversation, User
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from enum import Enum

router = APIRouter(prefix="/chat", tags=["Chat"])

class UserOut(BaseModel):
    user_id: str
    username: str
    avatar_url: str | None
    status: str
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    id: UUID
    other_user: UserOut
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int
    model_config = ConfigDict(from_attributes=True)


# Search user
@router.get("/users/search")
def search_users(other_user_name: str, current_user_id: str, db: Session = Depends(get_db)):
    return svc.search_users(db, other_user_name, current_user_id)


# List all conversations of current user
@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(current_user_id: str, db: Session = Depends(get_db)):
    return svc.get_conversations(db, current_user_id)


# Open or retrieve conversation
@router.post("/conversations")
def open_conversation(current_user_id: str, target_user_id: str, db: Session = Depends(get_db)):
    if current_user_id == target_user_id:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")
    conv = svc.get_or_create_conversation(db, current_user_id, target_user_id)
    return {"conversation_id": str(conv.conver_id)}


# Get conversation's messages
@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    before_timestamp: datetime = Query(default=None),
    db: Session = Depends(get_db)
):
    messages = svc.get_messages(
        db,
        conversation_id,
        before_timestamp=before_timestamp
    )
    return [
        {
            "id":              m.message_id,
            "conversation_id": m.conver_id,
            "sender_id":       m.sender_id,
            "sender_username": m.sender.username,
            "reply_to_id":     m.reply_to_id,
            "content":         m.content if not m.is_deleted else "[deleted]",
            "is_deleted":      m.is_deleted,
            "created_at":      m.created_at.isoformat(),
            "updated_at":      m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in messages
    ]


# Delete message
@router.delete("/messages/{message_id}")
def delete_message(
    message_id: str,
    current_user_id: str,
    confirm: bool,
    db: Session = Depends(get_db)
):
    result = svc.delete_message(db, message_id, current_user_id, confirm)

    if result == "cancelled":
        return {"ok": False, "message": "Delete cancelled by user"}

    if result == "not_found":
        raise HTTPException(status_code=404, detail="Message not found or not yours")

    return {"ok": True, "message": "Message deleted successfully"}


# Mark as read
@router.post("/conversations/{conversation_id}/read")
def mark_read(conversation_id: int, current_user_id: str, db: Session = Depends(get_db)):
    svc.mark_as_read(db, conversation_id, current_user_id)
    return {"ok": True}


# WebSocket stays async — it must be
@router.websocket("/chat/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):

    # Connect first
    await chat_manager.connect(websocket, user_id)

    from app.db_connection import SessionLocal

    db = SessionLocal()
    try:
        user = svc.get_user(db, user_id)
        if not user:
            await websocket.close(code=1008)
            return

        svc.set_user_status(db, user_id, "online")
        db.commit()

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "send_message":
                conv_id     = data["conversation_id"]
                content     = data["content"]
                reply_to_id = data.get("reply_to_id")

                saved = svc.save_message(db, conv_id, user, content, reply_to_id)
                conv  = db.query(Conversation).filter(Conversation.conver_id == conv_id).first()

                payload = {
                    "type":            "new_message",
                    "id":              str(saved.message_id),
                    "conversation_id": str(conv_id),
                    "sender_id":       str(user_id),
                    "sender_username": user.username,
                    "reply_to_id":     str(reply_to_id) if reply_to_id else None,
                    "content":         content,
                    "created_at":      saved.created_at.isoformat(),
                }

                await chat_manager.send_to_user(user_id, payload)

                if conv:
                    recipient_id = conv.user_b_id if conv.user_a_id == user_id else conv.user_a_id
                    await chat_manager.send_to_user(recipient_id, payload)

            elif action == "typing":
                await chat_manager.send_to_user(data["recipient_id"], {
                    "type":            "typing",
                    "conversation_id": data["conversation_id"],
                    "user_id":         user_id,
                })

            elif action == "mark_read":
                svc.mark_as_read(db, data["conversation_id"], user_id)
                await chat_manager.send_to_user(user_id, {
                    "type":            "read_receipt",
                    "conversation_id": data["conversation_id"],
                })

    except WebSocketDisconnect:
        chat_manager.disconnect(user_id)
        svc.set_user_status(db, user_id, "offline")
        db.commit()
    finally:
        db.close()