# All routes (endpoints)
from fastapi import APIRouter
from app.models.schemas import AnalyzeRequest
from app.services.decision_service import generate_decision

router = APIRouter()

@router.post("/analyze")
def analyze(data: AnalyzeRequest):
    return generate_decision(data)