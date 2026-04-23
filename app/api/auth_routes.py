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

router = APIRouter(prefix="/auth")


# -----------------------------google/github login--------------------------------

# 1. DYNAMIC BASE URL: 
# Uses Render environment variable if available, otherwise defaults to local
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

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
        user = resp.json()
        
        return {
            "status": "success",
            "provider": "github",
            "user": user
        }
    except MismatchingStateError:
        return HTMLResponse(content=ERROR_TEMPLATE.format(provider="github"), status_code=400)
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
        user = token.get("userinfo")
        return {"provider": "google", "user": user}
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
    invite_code: str = None
    
    @field_validator('username')
    @classmethod
    def username_rules(cls, v: str) -> str:
        # 1. Custom length catch
        if len(v) < 3:
            raise ValueError('Username is too short! It must be at least 3 characters.')
        

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
    
    ADMIN_SECRET_CODE = os.getenv("ADMIN_SIGNUP_CODE")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        
        if user.invite_code == ADMIN_SECRET_CODE:
            assigned_role = "Admin"
        else:
            assigned_role = "Client"
        

        cur.execute("SELECT username FROM users WHERE username = %s", (user.username,))
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=400, detail="username already registered, Please Try Another Username")

        # 1. Check if user exists
        cur.execute("SELECT email FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=400, detail="Email already registered, Please Try Another Email")

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

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username/Email and password are required"
        )

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 1. Update the query to include is_inactive
        query = "SELECT username, password, role, is_inactive FROM users WHERE username = %s OR email = %s;"
        cur.execute(query, (form_data.username, form_data.username))
        
        results = cur.fetchall()
        
        # 2. Check if user exists AND if they are inactive
        if not results:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_record = results[0]

        if user_record['is_inactive']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Verify password (rest of your logic remains the same)
        try:
            is_valid = verify_password(form_data.password, user_record['password'])
        except Exception as e:
            print(f"Bcrypt Verification Error: {e}")
            is_valid = False

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(
            data={"sub": user_record['username'], "role": user_record['role']}
        )

        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
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
        if conn:
            if 'cur' in locals() and cur:
                cur.close()
            conn.close()