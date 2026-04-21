# routes.py
from fastapi import APIRouter
from app.models.schemas import AnalyzeRequest      
from app.services.auth import authenticate_user
from app.models.schemas import LoginRequest, LoginResponse
from app.services.decision_service import generate_decision  

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