import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db_connection import get_db, get_db_connection
from app.models.models import User, Conversation, Message
from app.models.schemas import AdminUserUpdate
from sqlalchemy import or_
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.api.auth_routes import hash_password

router = APIRouter(prefix="/api", tags=["CRUD Operations"])


# ── User (self-service) ────────────────────────────────────────────────────────

@router.get("/user/get/{search_term}")
def get_user(search_term: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        or_(
            User.user_id == search_term,
            User.username == search_term,
            User.email == search_term
        )
    ).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with identifier '{search_term}' not found"
        )
    return user


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        return v


@router.patch("/user/update/{search_term}")
def update_user_profile(
    search_term: str,
    update_data: UserUpdate,
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(
        or_(
            User.user_id == search_term,
            User.username == search_term,
            User.email == search_term
        )
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if update_data.username:
        db_user.username = update_data.username
    if update_data.email:
        db_user.email = update_data.email
    if update_data.password:
        db_user.password = hash_password(update_data.password)

    db_user.last_seen_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(db_user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Update failed. Username or Email might already be taken."
        )

    return {"ok": True, "user": db_user}


@router.delete("/user/delete/{search_term}")
def delete_user(search_term: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        or_(
            User.user_id == search_term,
            User.username == search_term,
            User.email == search_term
        )
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        db.delete(db_user)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete user. They may have active messages or conversations linked to them."
        )

    return {"ok": True, "message": f"User {search_term} successfully purged."}


# ── Admin user management ──────────────────────────────────────────────────────

_USER_SAFE_COLUMNS = (
    "user_id, username, email, role, avatar_url, status, "
    "created_at, last_seen_at, is_inactive, token_used, max_token, token_refresh_at"
)

_ADMIN_ALLOWED_FIELDS = {"username", "email", "password", "role", "avatar_url", "status", "token_used", "max_token"}


@router.get("/admin/users")
def list_all_users():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(f"SELECT {_USER_SAFE_COLUMNS} FROM users ORDER BY created_at DESC")
    result = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


@router.patch("/admin/users/{user_id}")
def admin_update_user(user_id: str, data: AdminUserUpdate):
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items() if k in _ADMIN_ALLOWED_FIELDS}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    if "role" in updates and updates["role"] not in ("Admin", "Client"):
        raise HTTPException(status_code=400, detail="Role must be 'Admin' or 'Client'")
    if "password" in updates:
        updates["password"] = hash_password(updates["password"])

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [user_id]

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        f"UPDATE users SET {set_clause} WHERE user_id = %s RETURNING {_USER_SAFE_COLUMNS}",
        values,
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    result = dict(row)
    conn.commit()
    cur.close()
    conn.close()
    return result
