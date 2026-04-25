import os, shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session, aliased 
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timezone
from app.models.chat import User, Conversation, Message, ReadReceipt, MessageAttachment
from sqlalchemy import or_
from fastapi import HTTPException
from uuid import UUID, uuid4


# -- Get user ---------------------------------------------------------

def get_user(db: Session, user_id: str) -> User:
    return db.query(User).filter(User.user_id == user_id).first()

# Search user by name -----------------------------------------------------

def search_users(db: Session, query: str, my_user_id: str) -> list[dict]:
    me = db.query(User).filter(User.user_id == my_user_id).first()
    if not me:
        raise HTTPException(status_code=404, detail="Current user not found")

    users = (
        db.query(User)
        .filter(User.username.ilike(f"%{query}%"), User.user_id != my_user_id)
        .limit(10)
        .all()
    )

    results = []
    for u in users:
        # Auto-create conversation if none exists
        conv = get_or_create_conversation(db, my_user_id, u.user_id)

        results.append({
            "user_id":         u.user_id,
            "username":        u.username,
            "avatar_url":      u.avatar_url,
            "status":          u.status,
            "conversation_id": str(conv.conver_id),
        })

    return results


# -- Set user status ------------------------------------------------------

def set_user_status(db: Session, username: str, status: str):
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.status       = status
        user.last_seen_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Read Receipt Error: {e}")
        raise e


# -- IDs are stored in database ---------------------------

def get_or_create_conversation(db: Session, user_a_id: str, user_b_id: str) -> Conversation:
    a, b = (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)
    conv = db.query(Conversation).filter(
        Conversation.user_a_id == a,
        Conversation.user_b_id == b
    ).first()

    if not conv:
        conv = Conversation(user_a_id=a, user_b_id=b)
        db.add(conv)
        db.flush()         
        db.refresh(conv)   

        db.add(ReadReceipt(conver_id=conv.conver_id, user_id=user_a_id))
        db.add(ReadReceipt(conver_id=conv.conver_id, user_id=user_b_id))
        db.commit()
        db.refresh(conv)

    return conv


# ------------------ Get Conversations -----------------------------------

# Aliased for query
UserA = aliased(User, name="user_a")
UserB = aliased(User, name="user_b")

# Get Conversations
def get_conversations(db: Session, user_id: str) -> list[dict]:

    # Resolve username → User row → user_id
    user = db.query(User).filter(User.user_id.ilike(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find all conversations this user is part of
    query = (
        db.query(Conversation, UserA, UserB)
        .join(UserA, Conversation.user_a_id == UserA.user_id)
        .join(UserB, Conversation.user_b_id == UserB.user_id)
        .filter(or_(
            Conversation.user_a_id == user.user_id,
            Conversation.user_b_id == user.user_id
        ))
    )

    conversations = query.all()
    output = []

    for conv, user_a, user_b in conversations:
        other = user_b if conv.user_a_id == user.user_id else user_a

        last_msg = db.query(Message).filter(Message.conver_id == conv.conver_id)\
                     .order_by(Message.created_at.desc()).first()

        rr = db.query(ReadReceipt).filter(
            ReadReceipt.conver_id == conv.conver_id,
            ReadReceipt.user_id == user.user_id
        ).first()
        last_read = rr.last_read_at if rr else datetime.min.replace(tzinfo=timezone.utc)

        unread_count = db.query(func.count(Message.message_id)).filter(
            Message.conver_id == conv.conver_id,
            Message.sender_id != user.user_id,
            Message.created_at > last_read,
            Message.is_deleted == False
        ).scalar()

        output.append({
            "id": conv.conver_id,
            "other_user": {
                "user_id":    other.user_id,
                "username":   other.username,
                "avatar_url": other.avatar_url,
                "status":     other.status,      
            },
            "last_message":    last_msg.content if last_msg and not last_msg.is_deleted else None,
            "last_message_at": last_msg.created_at if last_msg else None,
            "unread_count":    unread_count,
        })

    output.sort(key=lambda x: x["last_message_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return output


# -- Get Messages ---------------------------------------------------------

def get_messages(db: Session, conversation_id: str, limit: int = 50, before_timestamp: datetime = None) -> list[Message]:
    query = (
        db.query(Message)
        .filter(Message.conver_id == conversation_id)
    )

    if before_timestamp:
        query = query.filter(Message.created_at < before_timestamp)

    query = (
        query
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    return list(reversed(query.all()))

# -- Save Messages ----------------------------------------------------

def save_message(db: Session, conversation_id: str, sender: User, content: str, reply_to_id: str = None) -> Message:
    msg = Message(
        conver_id=conversation_id,
        sender_id=sender.user_id,
        content=content,
        reply_to_id=reply_to_id
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# -- Delete Messages ------------------------------------------------------

def delete_message(db: Session, message_id: str, user_id: str, confirm: bool) -> str:
    if not confirm:
        return "cancelled"

    msg = db.query(Message).filter(
        Message.message_id == message_id,
        Message.sender_id == user_id
    ).first()

    if not msg:
        return "not_found"

    msg.is_deleted = True 
    db.commit() 
    return "deleted"


# -- Mark as Read ----------------------------------------------------------

def mark_as_read(db: Session, conversation_id: int, user_id: str):
    rr = db.query(ReadReceipt).filter(
        ReadReceipt.conver_id == conversation_id,
        ReadReceipt.user_id == user_id
    ).first()
    if rr:
        rr.last_read_at = datetime.now(timezone.utc)
    else:
        db.add(ReadReceipt(conver_id=conversation_id, user_id=user_id))
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Read Receipt Error: {e}")
        raise e


# -- File Upload Section --------------------------------------------------

ALLOWED_TYPES = {
    "image/jpeg": "image", "image/png": "image",
    "image/gif": "image",  "image/webp": "image",
    "text/csv": "csv",     "application/vnd.ms-excel": "csv",
    "application/pdf": "pdf",
    "application/vnd.ms-powerpoint": "pptx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "docx"
}

# File Uploadation
def upload_file(db: Session, conversation_id: str, current_user_id: str, file: UploadFile) -> dict:
    """Save the file, create a placeholder message, attach the file to it, and return payload."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only images, CSVs, PDFs, PPTXs, TXTs, DOCXs are allowed")

    user = get_user(db, current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Save a message whose content is the filename (acts as the "caption")
    msg = save_message(db, conversation_id, user, f"[file] {file.filename}")

    # Persist the file to disk and create the attachment row
    attachment = save_attachment(db, msg.message_id, file)

    return {
        "message_id":    str(msg.message_id),
        "conversation_id": conversation_id,
        "sender_id":     current_user_id,
        "sender_username": user.username,
        "content":       f"[file] {file.filename}",
        "created_at":    msg.created_at.isoformat(),
        "attachment": {
            "attachment_id": str(attachment.attachment_id),
            "file_name":     attachment.file_name,
            "file_type":     attachment.file_type,
            "file_size":     attachment.file_size,
        }
    }

# Save file attachment to database and file system
def save_attachment(db: Session, message_id: UUID, file: UploadFile) -> MessageAttachment:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only images, CSVs, PDFs, PPTXs, TXTs, DOCXs are allowed")

    file_type = ALLOWED_TYPES[file.content_type]

    # Read file into memory (BLOB)
    file_data = file.file.read()
    file_size = len(file_data)

    attachment = MessageAttachment(
        message_id=message_id,
        file_name=file.filename,
        file_type=file_type,
        file_data=file_data,
        file_size=file_size,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment

