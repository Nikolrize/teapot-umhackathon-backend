from fastapi import APIRouter
from starlette.requests import Request  # Direct import often bypasses FastAPI's wrapper logic
from app.services.oauth_service import oauth

router = APIRouter(prefix="/auth")

@router.get("/github/login")
async def github_login(request: Request):
    redirect_uri = "http://localhost:8000/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def github_callback(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        # Check if token is valid
        if not token:
            return {"error": "Failed to get token"}
        
        resp = await oauth.github.get("user", token=token)
        return resp.json()
    except Exception as e:
        print(f"DETAILED ERROR: {str(e)}") # LOOK AT YOUR TERMINAL FOR THIS
        return {"error": str(e)}
    
@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    return {"provider": "google", "user": user}