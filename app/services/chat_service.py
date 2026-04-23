from sqlalchemy.orm import Session, aliased 
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timezone
from app.models.chat import User, Conversation, Message, ReadReceipt
<<<<<<< HEAD
from fastapi import HTTPException
=======
from sqlalchemy import or_
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42

# Get or create user
def get_or_create_user(db: Session, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

<<<<<<< HEAD
# Search user by name
def search_users(db: Session, query: str, username: str) -> list[User]:
    return (
        db.query(User)
        .filter(User.username.ilike(f"%{query}%"), User.username != username)
=======
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
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42
        .limit(10)
        .all()
    )

<<<<<<< HEAD
# Set user status
def set_user_status(db: Session, username: str, status: str):
    user = db.query(User).filter(User.username == username).first()
=======
def set_user_status(db: Session, user_id: str, status: str):
    user = db.query(User).filter(User.user_id == user_id).first()
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42
    if user:
        user.status       = status
        user.last_seen_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Read Receipt Error: {e}")
        raise e

# IDs are stored in database
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
        db.add(ReadReceipt(conver_id=conv.conver_id, user_id=user_a_id))
        db.add(ReadReceipt(conver_id=conv.conver_id, user_id=user_b_id))
        db.commit()
        db.refresh(conv)
    return conv

<<<<<<< HEAD
# List conversations of current user
def get_conversations(db: Session, user_id: str, search_query: str = None) -> list[dict]:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create aliases for the User table to represent the two sides of the conversation
    UserA = aliased(User)
    UserB = aliased(User)

    # Start the query
    query = (
=======
def get_conversations(db: Session, user_id: str) -> list[dict]:
    conversations = (
>>>>>>> a3251f4bb394e063d1bcee5efcd60aef72c74c42
        db.query(Conversation)
        .join(UserA, Conversation.user_a_id == UserA.user_id)
        .join(UserB, Conversation.user_b_id == UserB.user_id)
        .filter(or_(
            Conversation.user_a_id == user.user_id,
            Conversation.user_b_id == user.user_id
        ))
    )

    # 2. Apply search filter if a query is provided
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            or_(
                # If current user is A, search for username of B
                and_(Conversation.user_a_id == user.user_id, UserB.username.ilike(search_filter)),
                # If current user is B, search for username of A
                and_(Conversation.user_b_id == user.user_id, UserA.username.ilike(search_filter))
            )
        )

    conversations = query.all()

    output = []
    for conv in conversations:
        other = conv.user_b if conv.user_a_id == user.user_id else conv.user_a

        last_msg = (
            db.query(Message)
            .filter(Message.conver_id == conv.conver_id)
            .order_by(Message.created_at.desc())
            .first()
        )

        rr = db.query(ReadReceipt).filter(
            ReadReceipt.conver_id == conv.conver_id,
            ReadReceipt.user_id == user.user_id
        ).first()
        last_read = rr.last_read_at if rr else datetime.min.replace(tzinfo=timezone.utc)

        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.conver_id == conv.conver_id, 
                Message.sender_id != user.user_id,
                Message.created_at > last_read,
                Message.is_deleted == False
            )
            .scalar()
        )

        output.append({
            "id":              conv.conver_id,
            "other_user":      other,
            "last_message":    last_msg.content if last_msg and not last_msg.is_deleted else None,
            "last_message_at": last_msg.created_at if last_msg else None,
            "unread_count":    unread_count,
        })

    output.sort(
        key=lambda x: x["last_message_at"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
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