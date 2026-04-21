# routes.py
from fastapi import APIRouter
from app.models.schemas import AnalyzeRequest, LoginRequest, LoginResponse      
from app.services.auth import authenticate_user
from app.services.decision_service import generate_decision  
from app.services.oauth_service import oauth
from starlette.requests import Request 

router = APIRouter() 

@router.post("/analyze")
def analyze(data: AnalyzeRequest):
    return generate_decision(data)

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    result = authenticate_user(data.username, data.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result

# #-------------------------------hardcoded url----------------------------------
# @router.get("/github/login")
# async def github_login(request: Request):
#     redirect_uri = "http://localhost:8000/auth/github/callback"
#     return await oauth.github.authorize_redirect(request, redirect_uri)

# @router.get("/google/login")
# async def google_login(request: Request):
#     redirect_uri = "http://localhost:8000/auth/google/callback"  
#     return await oauth.google.authorize_redirect(request, redirect_uri)