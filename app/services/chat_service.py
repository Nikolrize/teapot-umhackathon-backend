from sqlalchemy.orm import Session 
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timezone
from app.models.chat import User, Conversation, Message, ReadReceipt
from sqlalchemy import or_

def get_or_create_user(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def search_users(db: Session, query: str, exclude_id: str) -> list[User]:
    if not query.strip():
        return []
    
    return (
            db.query(User)
            .filter(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.email.ilike(f"%{query}%")
                ),
                User.user_id != exclude_id
            )
        .limit(10)
        .all()
    )

def set_user_status(db: Session, user_id: str, status: str):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.status       = status
        user.last_seen_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Read Receipt Error: {e}")
        raise e

def get_or_create_conversation(db: Session, user_id_1: str, user_id_2: str) -> Conversation:
    a, b = (user_id_1, user_id_2) if user_id_1 < user_id_2 else (user_id_2, user_id_1)
    conv = db.query(Conversation).filter(
        Conversation.user_a_id == a,
        Conversation.user_b_id == b
    ).first()

    if not conv:
        conv = Conversation(user_a_id=a, user_b_id=b)
        db.add(conv)
        db.flush()
        db.add(ReadReceipt(conversation_id=conv.id, user_id=user_id_1))
        db.add(ReadReceipt(conversation_id=conv.id, user_id=user_id_2))
        db.commit()
        db.refresh(conv)
    return conv

def get_conversations(db: Session, user_id: str) -> list[dict]:
    conversations = (
        db.query(Conversation)
        .filter(or_(
            Conversation.user_a_id == user_id,
            Conversation.user_b_id == user_id
        ))
        .all()
    )

    output = []
    for conv in conversations:
        other    = conv.user_b if conv.user_a_id == user_id else conv.user_a
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        rr = db.query(ReadReceipt).filter(
            ReadReceipt.conversation_id == conv.id,
            ReadReceipt.user_id == user_id
        ).first()
        last_read = rr.last_read_at if rr else datetime.min.replace(tzinfo=timezone.utc)

        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.conversation_id == conv.id,
                Message.sender_id != user_id,
                Message.created_at > last_read,
                Message.is_deleted == False
            )
            .scalar()
        )

        output.append({
            "id":              conv.id,
            "other_user":      other,
            "last_message":    last_msg.content if last_msg and not last_msg.is_deleted else None,
            "last_message_at": last_msg.created_at if last_msg else None,
            "unread_count":    unread_count,
        })

    output.sort(key=lambda x: x["last_message_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return output

def get_messages(db: Session, conversation_id: int, limit: int = 50, before_id: int = None) -> list[Message]:
    query = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if before_id:
        query = query.filter(Message.id < before_id)
    return list(reversed(query.all()))

def save_message(db: Session, conversation_id: int, sender: User, content: str, reply_to_id: int = None) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender.id,
        content=content,
        reply_to_id=reply_to_id
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def delete_message(db: Session, message_id: int, user_id: str) -> bool:
    msg = db.query(Message).filter(
        Message.message_id == message_id,
        Message.sender_id == user_id
    ).first()
    if not msg:
        return False
    msg.is_deleted = True
    db.commit()
    return True

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