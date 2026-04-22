import os
import re
import bcrypt
import psycopg2
from fastapi import APIRouter, HTTPException, status
from starlette.requests import Request
from app.services.oauth_service import oauth
from pydantic import BaseModel, EmailStr, field_validator
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.base_client.errors import MismatchingStateError
from pydantic import BaseModel, EmailStr, Field
from app.db_connection import get_db_connection

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

def verify_password(plain_password, hashed_password):
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)



class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)    
    confirm_password: str
    role: str = "Client"

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
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
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Check if user exists
        cur.execute("SELECT email FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            cur.close()
            raise HTTPException(status_code=400, detail="Email already registered")

        # 2. Insert (Trigger handles the ID)
        query = """
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, role;
        """
        cur.execute(query, (user.username, user.email, hashed_pwd, user.role))
        new_user = cur.fetchone()
        
        conn.commit()
        cur.close()

        return {
            "status": "success",
            "user": {"id": new_user[0], "username": new_user[1], "role": new_user[2]}
        }

    except Exception as e:
        if conn: conn.rollback()
        print(f"Signup Error: {e}")
        # Return the actual error to help you debug
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn: conn.close()