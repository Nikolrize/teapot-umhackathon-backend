import psycopg2.extras
import re
from fastapi import UploadFile, File,APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db_connection import get_db, get_db_connection
from app.models.models import User, Conversation, Message
from app.models.schemas import AdminUserUpdate
from sqlalchemy import or_ , text
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.api.auth_routes import hash_password
from app.core.security import get_current_user
import psycopg2.extras
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
# from app.models.schemas import UserUpdate, MessageUpdate
from app.core.config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
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
#def update_user_profile(
#    search_term: str,
#    update_data: UserUpdate,
#    db: Session = Depends(get_db)
#):
def update_user_profile(search_term: str, update_data: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        or_(User.user_id == search_term, User.username == search_term, User.email == search_term)
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # NEW: Catch OAuth users who haven't set a password yet
    if db_user.password is None:
        raise HTTPException(
            status_code=403, 
            detail="To edit your profile, you must first set a local password for your account."
        )

    # Proceed with updates if they have a password
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


class SetInitialPassword(BaseModel):
    new_password: str = Field(..., min_length=8)

@router.post("/user/set-initial-password/{user_id}")
def set_initial_password(user_id: str, data: SetInitialPassword, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.user_id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Safety Check: If they already have a password, they should use the "Change Password" flow
    if db_user.password is not None:
        raise HTTPException(
            status_code=400, 
            detail="Password already exists!"
        )
    try:
        # Hash and Save
        db_user.password = hash_password(data.new_password)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to set password")

    return {"ok": True, "message": "Password created!"}


@router.delete("/user/delete/{search_term}")
def delete_user(search_term: str, db: Session = Depends(get_db)):
    # 1. Search for the target user (active or already inactive)
    db_user = db.query(User).filter(
        or_(
            User.user_id == search_term,
            User.username == search_term,
            User.email == search_term
        )
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Check if they are already deleted to avoid redundant commits
    if db_user.is_inactive == True:
        return {"ok": True, "message": "User is already deactivated."}
    
    # 3. Perform Soft Delete
    try:
        db_user.is_inactive = True
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

MOCK_MASTER_ADMIN = {
    "id": "ADM0004",
    "username": "Yagoo",
    "role": "Master Admin"
}

# This is a dummy function to replace your real auth for this test
async def get_mock_user():
    return MOCK_MASTER_ADMIN

class AdminUserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str  

@router.post("/admin/users/create", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    payload: AdminUserCreateSchema, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Re-injecting the current user
):
    try:
        # 1. AUTHENTICATION: Only Admins or Master Admins can access this endpoint at all
        allowed_creators = ['Admin', 'Master Admin']
        if current_user['role'] not in allowed_creators:
            raise HTTPException(
                status_code=403, 
                detail="You do not have permission to perform this action."
            )

        # 2. ROLE HIERARCHY CHECK: Standard Admins cannot create other Admins
        if current_user['role'] == 'Admin' and payload.role == 'Admin':
            raise HTTPException(
                status_code=403, 
                detail="Standard Admins can only create Client accounts. Contact Master Admin to perform this action"
            )

        # 3. SECURITY CHECK: Block 'Master Admin' creation entirely via API
        if payload.role == 'Master Admin':
            raise HTTPException(
                status_code=403, 
                detail="Master Admin accounts cannot be created via this API for security reasons."
            )

        # --- DATABASE LOGIC ---

        check_query = text("SELECT is_inactive, username, email FROM users WHERE username = :u OR email = :e")
        existing_user = db.execute(check_query, {"u": payload.username, "e": payload.email}).mappings().fetchone()

        if existing_user:
            if existing_user['username'] == payload.username:
                raise HTTPException(status_code=400, detail="Username already registered.")
            if existing_user['is_inactive']:
                raise HTTPException(status_code=403, detail="This account has been deactivated.")
            raise HTTPException(status_code=400, detail="Email already registered.")

        hashed_pwd = hash_password(payload.password)
        
        # INSERT
        insert_query = text("""
            INSERT INTO users (username, email, password, role)
            VALUES (:username, :email, :password, :role)
            RETURNING user_id, username, role;
        """)
        
        result = db.execute(insert_query, {
            "username": payload.username,
            "email": payload.email,
            "password": hashed_pwd,
            "role": payload.role
        })
        
        new_user = result.mappings().fetchone()
        db.commit() # SQLAlchemy requires explicit commit

        return {
            "status": "success",
            "user": {
                "id": new_user['user_id'], 
                "username": new_user['username'], 
                "role": new_user['role']
            }
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Admin Create Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        db.close()

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

@router.patch("/users/update/avatar")
async def update_avatar(
    file: UploadFile = File(...), 
    current_user: dict = Depends(get_mock_user)
):
    # 2. Validation: Check if it's an image
    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image format.")

    conn = None
    try:
        # Pass the file stream directly
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="teapot_avatars",
            public_id=f"user_{current_user['id']}",
            overwrite=True,
            transformation=[
                {'width': 500, 'height': 500, 'crop': "fill", 'gravity': "face"}
            ]
        )   

        # 4. Get the optimized URL
        # secure_url is the https link to the image
        new_avatar_url = upload_result.get("secure_url")

        # 5. Update your PostgreSQL VARCHAR column
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "UPDATE users SET avatar_url = %s WHERE user_id = %s"
        cur.execute(query, (new_avatar_url, current_user['id']))
        conn.commit()

        return {
            "status": "success",
            "message": "Avatar uploaded!",
            "avatar_url": new_avatar_url
        }

    except Exception as e:
        if conn: conn.rollback()
        print(f"Cloudinary/DB Error: {e}")
        raise HTTPException(status_code=500, detail="Cloud upload failed.")
    finally:
        if conn: conn.close()

