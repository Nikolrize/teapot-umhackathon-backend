from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session 
from app.db_connection import get_db
from app.services.chat_manager import chat_manager
from app.services import chat_service as svc
from app.models.chat import Conversation

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/users/search")
def search_users(q: str, me: str, db: Session = Depends(get_db)): 
    return svc.search_users(db, q, exclude_id=me)

@router.get("/conversations")
def list_conversations(user_id: str, db: Session = Depends(get_db)):
    return svc.get_conversations(db, user_id)

# @router.post("/conversations")
# def open_conversation(user_id: str, target_id: int, db: Session = Depends(get_db)):
#     if user_id == target_id:
#         raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")
#     conv = svc.get_or_create_conversation(db, user_id, target_id)
#     return {"conversation_id": conv.id}

# @router.get("/conversations/{conversation_id}/messages")
# def get_messages(
#     conversation_id: int,
#     limit:     int = Query(default=50, le=100),
#     before_id: int = Query(default=None),
#     db: Session = Depends(get_db)
# ):
#     messages = svc.get_messages(db, conversation_id, limit, before_id)
#     return [
#         {
#             "id":              m.id,
#             "conversation_id": m.conversation_id,
#             "sender_id":       m.sender_id,
#             "sender_username": m.sender.username,
#             "reply_to_id":     m.reply_to_id,
#             "content":         m.content if not m.is_deleted else "[deleted]",
#             "is_deleted":      m.is_deleted,
#             "created_at":      m.created_at.isoformat(),
#             "updated_at":      m.updated_at.isoformat() if m.updated_at else None,
#         }
#         for m in messages
#     ]

@router.delete("/messages/{message_id}")
def delete_message(message_id: int, user_id: str, db: Session = Depends(get_db)):
    success = svc.delete_message(db, message_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or not yours")
    return {"ok": True}

@router.post("/conversations/{conversation_id}/read")
def mark_read(conversation_id: int, user_id: str, db: Session = Depends(get_db)):
    svc.mark_as_read(db, conversation_id, user_id)
    return {"ok": True}

# WebSocket stays async — it must be
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
    user = svc.get_or_create_user(db, str(user_id))
    await chat_manager.connect(websocket, user_id)
    svc.set_user_status(db, user_id, "online")

    try:
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
                    "id":              saved.message_id,
                    "conversation_id": conv_id,
                    "sender_id":       user_id,
                    "sender_username": user.username,
                    "reply_to_id":     reply_to_id,
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