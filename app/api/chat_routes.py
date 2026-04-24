from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session 
from app.db_connection import get_db
from app.services.chat_manager import chat_manager
from app.services import chat_service as svc
from app.models.chat import Conversation, MessageAttachment
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile, File
from fastapi.responses import Response
from uuid import UUID


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


# -- Route: Search user ----------------------------------------------------------

@router.get("/users/search")
def search_users(other_user_name: str, current_user_id: str, db: Session = Depends(get_db)):
    return svc.search_users(db, other_user_name, current_user_id)


# -- Route: List all conversations of current user ---------------------------------

@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(current_user_id: str, db: Session = Depends(get_db)):
    return svc.get_conversations(db, current_user_id)


# -- Route: Open or retrieve conversation ----------------------------------------

@router.post("/conversations")
def open_conversation(current_user_id: str, target_user_id: str, db: Session = Depends(get_db)):
    if current_user_id == target_user_id:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")
    conv = svc.get_or_create_conversation(db, current_user_id, target_user_id)
    return {"conversation_id": str(conv.conver_id)}


# -- Route: Get conversation's messages --------------------------------------------

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
            "attachment": (
                {
                    "attachment_id": str(m.attachments[0].attachment_id),
                    "file_name":     m.attachments[0].file_name,
                    "file_type":     m.attachments[0].file_type,
                    "file_size":     m.attachments[0].file_size,
                } if m.attachments else None
            ),
            "is_deleted":      m.is_deleted,
            "created_at":      m.created_at.isoformat(),
            "updated_at":      m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in messages
    ]


# -- Route: Delete message -----------------------------------------------------

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


# -- Route: Mark as read -----------------------------------------------------------

@router.post("/conversations/{conversation_id}/read")
def mark_read(conversation_id: int, current_user_id: str, db: Session = Depends(get_db)):
    svc.mark_as_read(db, conversation_id, current_user_id)
    return {"ok": True}

# -- Route: Upload file (included image, .csv, .pdf) ---------------------------------

@router.post("/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: str,
    current_user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    payload = svc.upload_file(db, conversation_id, current_user_id, file)

    # Broadcast to sender + recipient via WebSocket (same pattern as send_message)
    ws_payload = {"type": "new_message", **payload}
    await chat_manager.send_to_user(current_user_id, ws_payload)

    conv = db.query(Conversation).filter(Conversation.conver_id == conversation_id).first()
    if conv:
        recipient_id = conv.user_b_id if conv.user_a_id == current_user_id else conv.user_a_id
        await chat_manager.send_to_user(recipient_id, ws_payload)

    return payload


# -- Endpoint Attachment (Debug Use) --------------------------------------------

@router.get("/attachments/{attachment_id}/debug")
def debug_attachment(attachment_id: str, db: Session = Depends(get_db)):
    att = db.query(MessageAttachment).filter(
        MessageAttachment.attachment_id == attachment_id
    ).first()

    return {
        "file_name": att.file_name,
        "file_type": att.file_type,
        "size": len(att.file_data),
    }

# -- Download Attachment --------------------------------------------

@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: str, db: Session = Depends(get_db)):

    att = db.query(MessageAttachment).filter(
        MessageAttachment.attachment_id == attachment_id
    ).first()

    if not att:
        raise HTTPException(status_code=404, detail="File not found")

    if not att.file_data:
        raise HTTPException(status_code=404, detail="File data missing")

    return Response(
        content=att.file_data,
        media_type=att.file_type,
        headers={
            # forces download instead of opening in browser
            "Content-Disposition": f'attachment; filename="{att.file_name}"'
        }
    )

# -- WebSocket stays async — it must be --------------------------------------

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