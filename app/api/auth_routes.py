import os
from fastapi import APIRouter
from starlette.requests import Request
from app.services.oauth_service import oauth
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.base_client.errors import MismatchingStateError

router = APIRouter(prefix="/auth")

# 1. DYNAMIC BASE URL: 
# Uses Render environment variable if available, otherwise defaults to local
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

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