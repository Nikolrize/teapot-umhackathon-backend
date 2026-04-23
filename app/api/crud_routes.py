from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db_connection import get_db
from app.models.models import User, Conversation, Message
from sqlalchemy import or_
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.api.auth_routes import hash_password

# from app.models.schemas import UserUpdate, MessageUpdate

router = APIRouter(prefix="/api", tags=["CRUD Operations"])

# ------------------------------------user table---------------------------------

@router.get("/user/get/{search_term}")
def get_user(search_term: str, db: Session = Depends(get_db)):
    # We search across user_id, username, and email
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
        db_user.password = update_data.password
    
    # 3. Auto-update last seen
    db_user.last_seen_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(db_user)
    except SQLAlchemyError as e:
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
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Delete Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to deactivate user account."
        )
        
    return {"ok": True, "message": f"User {search_term} has been deactivated."}
