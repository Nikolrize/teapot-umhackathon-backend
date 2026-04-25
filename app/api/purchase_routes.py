from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.purchase_service import process_purchase, get_purchase_history
from app.services.token_service import get_token_status

router = APIRouter(prefix="/purchase")


class PurchaseRequest(BaseModel):
    user_id: str
    purchase_type: str = "token"


@router.post("")
def make_purchase(data: PurchaseRequest):
    """
    MVP purchase — no payment gateway.
    Records the purchase and credits purchased_token_remaining immediately.
    """
    if data.purchase_type != "token":
        raise HTTPException(status_code=400, detail="Only 'token' purchase type is supported.")
    try:
        return process_purchase(data.user_id, data.purchase_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{user_id}")
def purchase_history(user_id: str):
    """List all purchases made by a user."""
    return get_purchase_history(user_id)


@router.get("/token-status/{user_id}")
def token_status(user_id: str):
    """
    Return the user's current token breakdown:
    - token_used, max_token, purchased_token_remaining
    - total_available, tokens_remaining, token_refresh_at
    """
    status = get_token_status(user_id)
    if not status:
        raise HTTPException(status_code=404, detail="User not found")
    return status
