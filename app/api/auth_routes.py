import os
import re
import bcrypt
import psycopg2.extras
# from . import auth_utils
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.services.oauth_service import oauth
from pydantic import BaseModel, EmailStr, field_validator
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.base_client.errors import MismatchingStateError
from pydantic import BaseModel, EmailStr, Field
from app.db_connection import get_db_connection
from .auth_utils import create_access_token
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy import text
router = APIRouter(prefix="/auth")

def get_db_connection():
    # Reuse your existing connection logic here
    return psycopg2.connect(os.getenv("DATABASE_URL"))

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# -----------------------------google/github login--------------------------------

# 1. DYNAMIC BASE URL: 
# Uses Render environment variable if available, otherwise defaults to local

# BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/") #local
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/") #render deployment

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def sync_oauth_user_to_db(provider_data: dict, provider_name: str):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Normalize Identity info
        p_id = str(provider_data.get('sub') or provider_data.get('id'))
        email = provider_data.get('email')
        username = provider_data.get('name') or provider_data.get('login') or f"{provider_name}_user_{p_id[:5]}"

        # 1. Search existing user
        cur.execute("SELECT * FROM users WHERE provider_id = %s OR email = %s;", (p_id, email))
        db_user = cur.fetchone()

        if db_user:
            if db_user['is_inactive']:
                raise HTTPException(status_code=403, detail="Account deactivated. Contact support.")
            
            # Sync provider info if they previously used local login
            cur.execute(
                "UPDATE users SET last_seen_at = %s, auth_provider = %s, provider_id = %s WHERE user_id = %s",
                (datetime.now(timezone.utc), provider_name, p_id, db_user['user_id'])
            )
            user_record = db_user
        else:
            # 2. Insert New User (Trigger handles CLI ID)
            query = """
                INSERT INTO users (username, email, role, auth_provider, provider_id, is_inactive)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id, username, role;
            """
            cur.execute(query, (username, email, 'Client', provider_name, p_id, False))
            user_record = cur.fetchone()

        conn.commit()
        
        # 3. Create your JWT Token
        access_token = create_access_token(data={"sub": user_record['username'], "role": user_record['role']})
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_record['user_id'],
                "username": user_record['username']
            }
        }
    finally:
        conn.close()

@router.get("/github/login")
async def github_login(request: Request):
    request.session.clear() 
    redirect_uri = f"{BASE_URL}/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def github_callback(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get("user", token=token)
        user_data = resp.json()
        
        # GitHub Email privacy fallback
        if not user_data.get('email'):
            email_resp = await oauth.github.get("user/emails", token=token)
            user_data['email'] = next(e['email'] for e in email_resp.json() if e['primary'])

        return sync_oauth_user_to_db(user_data, "github")
    except Exception as e:
        return {"error": str(e)}

@router.get("/google/login")
async def google_login(request: Request):
    request.session.clear() 
    redirect_uri = f"{BASE_URL}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        return sync_oauth_user_to_db(token.get("userinfo"), "google")
    except MismatchingStateError:
        return HTMLResponse(content=ERROR_TEMPLATE.format(provider="google"), status_code=400)
    except Exception as e:
        return {"error": str(e)}
@router.get("/reset")
async def reset_session(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/")
    response.delete_cookie("fastapi_session") 
    return response

# Plain HTML template without styles
ERROR_TEMPLATE = """
    <html>
        <body>
            <h1>Session Mismatch (CSRF Warning)</h1>
            <p>Your login session could not be verified. This happens if you stay on the login page too long or have old cookies.</p>
            <div>
                <a href="/auth/{provider}/login">Try Again</a>
                <p>Still having trouble? <a href="/auth/reset">Click here to clear all cookies</a></p>
            </div>
        </body>
    </html>
"""


# --------------------------------------------signup----------------------------------------------


def hash_password(password: str):
    # Convert password to bytes, generate salt, and hash
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8') # Store as string in DB

def verify_password(plain_password: str, hashed_password: str):
    if not hashed_password:
        return False
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)    
    confirm_password: str
    
    
    @field_validator('username')
    @classmethod
    def username_rules(cls, v: str) -> str:
        # 1. Catch empty strings or just whitespace
        if not v.strip():
             raise ValueError('Username cannot be empty.')
             
        # 2. Length check
        if len(v) < 3:
            raise ValueError('Username is too short! It must be at least 3 characters.')
            
        # 3. Optional: Character check (no special characters)
        if not v.isalnum():
            raise ValueError('Username must only contain letters and numbers.')
            
        return v

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password is too short! It must be at least 8 characters long')
        if len(v) > 50:
            raise ValueError('Password is too long! It must be less then 50 charcters long')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values.data and v != values.data['password']:
            raise ValueError('Passwords do not match! Pls try again')
        return v    
    
@router.post("/signup")
async def signup(user: SignupRequest):
    hashed_pwd = hash_password(user.password)
    conn = None
    cur = None
    

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        

        assigned_role = "Client"
        
        cur.execute("SELECT username FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=400, detail="username already registered, Please Try Another Username")

        cur.execute(
            "SELECT is_inactive, auth_provider FROM users WHERE email = %s", 
            (user.email,)
        )
        existing_user = cur.fetchone()

        if existing_user:
            # Check 1: Is the account deactivated? (Highest priority)
            if existing_user['is_inactive']:
                cur.close()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="This account has been deactivated. Please contact support@teapot.gmail.com for more detail."
                )

            # Check 2: Is this an OAuth account trying to sign up manually?
            provider = existing_user['auth_provider']
            if provider != 'local':
                cur.close()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail=f"This email is already registered via {provider.title()}. "
                           f"Please login with {provider.title()} first to link a password."
                )

            # Check 3: General "Email Taken" error for active local users
            cur.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already registered. Please try another email or log in."
            )
        
        # 2. Insert (Trigger handles the ID)
        query = """
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, username, role;
        """
        cur.execute(query, (user.username, user.email, hashed_pwd, assigned_role))
        new_user = cur.fetchone()

        if not new_user:
            # Rollback if we didn't get a user back for some reason
            conn.rollback()
            raise HTTPException(
                status_code=500, 
                detail="Database error: User creation failed to return data."
            ) 
        conn.commit()
        

        return {
            "status": "success",
            "user": {"id": new_user[0], "username": new_user[1], "role": new_user[2]}
        }
    except HTTPException:
        # Re-raise planned HTTP errors
        raise

    except Exception as e:
        if conn: conn.rollback()
        print(f"Signup Error: {e}")
        # Return the actual error to help you debug
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: conn.close()
# ----------------------------------login-------------------------------
class LoginSchema(BaseModel):
    username: str
    password: str
    
@router.post("/login")
async def login(payload: LoginSchema):
    conn = None
    try:
        conn = get_db_connection() 
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


        query = """
            SELECT user_id, username, password, role, is_inactive 
            FROM users 
            WHERE username = %s OR email = %s;
        """
        cur.execute(query, (payload.username, payload.username))
        user_record = cur.fetchone()

        if not user_record:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user_record['is_inactive']:
            raise HTTPException(
                status_code=403, 
                detail="This account has been deactivated. Contact support@teapot.gmail.com."
            )

        # 5. Verify Password
        if not verify_password(payload.password, user_record['password']):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # 6. Generate Token
        access_token = create_access_token(
            data={
                "sub": user_record['username'], 
                "id": str(user_record['user_id']), 
                "role": user_record['role']
            }
        )

        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_record['user_id'], 
                "username": user_record['username'],
                "role": user_record['role']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # 7. CRITICAL: Always close raw psycopg2 connections manually
        if 'cur' in locals() and cur: cur.close()
        if conn: conn.close()


    #test