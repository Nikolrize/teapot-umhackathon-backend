from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session 
from app.db_connection import get_db
from app.services.chat_manager import chat_manager
from app.services import chat_service as svc
from app.models.chat import Conversation
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["Chat"])

class UserOut(BaseModel):
    user_id: str
    username: str
    avatar_url: str | None
    status: str
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    id: int
    other_user: UserOut
    last_message: str | None
    last_message_at: datetime | None
    unread_count: int
    model_config = ConfigDict(from_attributes=True)

# Search user
@router.get("/users/search")
<<<<<<< HEAD
def search_users(other_user: str, my_name: str, db: Session = Depends(get_db)):
    return svc.search_users(db, other_user, my_name)

# List all conversations of current user
@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(username: str, 
                       db: Session = Depends(get_db)
                       # ,current_user: User = Depends(get_current_user)):
                      ):
    return svc.get_conversations(db, username) 
    # return svc.get_conversations(db, current_user.username)
    

# Open or retrieve conversation
# @router.post("/conversations")
# def open_conversation(username: str, target_username: str, db: Session = Depends(get_db)):
#     if username == target_username:
#         raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")
#     conv = svc.get_or_create_conversation(db, username, target_username)
#     return {"conversation_id": conv.conver_id}
=======
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
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42

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

<<<<<<< HEAD
# @router.delete("/messages/{message_id}")
# def delete_message(message_id: int, user_id: str, db: Session = Depends(get_db)):
#     success = svc.delete_message(db, message_id, user_id)
#     if not success:
#         raise HTTPException(status_code=404, detail="Message not found or not yours")
#     return {"ok": True}

# @router.post("/conversations/{conversation_id}/read")
# def mark_read(conversation_id: int, user_id: str, db: Session = Depends(get_db)):
#     svc.mark_as_read(db, conversation_id, user_id)
#     return {"ok": True}

# # WebSocket stays async
# @router.websocket("/ws/{user_id}")
# async def websocket_endpoint(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
#     user = svc.get_or_create_user(db, str(user_id))
#     await chat_manager.connect(websocket, user_id)
#     svc.set_user_status(db, user_id, "online")
=======
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
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42

#     try:
#         while True:
#             data = await websocket.receive_json()
#             action = data.get("action")

#             if action == "send_message":
#                 conv_id     = data["conversation_id"]
#                 content     = data["content"]
#                 reply_to_id = data.get("reply_to_id")

<<<<<<< HEAD
#                 saved = svc.save_message(db, conv_id, user, content, reply_to_id)
#                 conv  = db.query(Conversation).filter(Conversation.id == conv_id).first()

#                 payload = {
#                     "type":            "new_message",
#                     "id":              saved.id,
#                     "conversation_id": conv_id,
#                     "sender_id":       user_id,
#                     "sender_username": user.username,
#                     "reply_to_id":     reply_to_id,
#                     "content":         content,
#                     "created_at":      saved.created_at.isoformat(),
#                 }
=======
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
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42

#                 await chat_manager.send_to_user(user_id, payload)

#                 if conv:
#                     recipient_id = conv.user_b_id if conv.user_a_id == user_id else conv.user_a_id
#                     await chat_manager.send_to_user(recipient_id, payload)

#             elif action == "typing":
#                 await chat_manager.send_to_user(data["recipient_id"], {
#                     "type":            "typing",
#                     "conversation_id": data["conversation_id"],
#                     "user_id":         user_id,
#                 })

#             elif action == "mark_read":
#                 svc.mark_as_read(db, data["conversation_id"], user_id)
#                 await chat_manager.send_to_user(user_id, {
#                     "type":            "read_receipt",
#                     "conversation_id": data["conversation_id"],
#                 })

#     except WebSocketDisconnect:
#         chat_manager.disconnect(user_id)
#         svc.set_user_status(db, user_id, "offline")