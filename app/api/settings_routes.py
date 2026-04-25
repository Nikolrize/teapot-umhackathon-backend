from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.purchase_service import get_all_settings, get_setting, upsert_setting

router = APIRouter(prefix="/settings")


class SettingUpsertRequest(BaseModel):
    setting_value: int
    price: Optional[str] = None


@router.get("")
def list_settings():
    """List all system settings (token pack size, prices, etc.)."""
    return get_all_settings()


@router.get("/{setting_key}")
def get_setting_detail(setting_key: str):
    setting = get_setting(setting_key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{setting_key}' not found")
    return setting


@router.put("/{setting_key}")
def set_setting(setting_key: str, data: SettingUpsertRequest):
    """
    Create or update a system setting.
    Common keys:
      - token_pack  → setting_value = tokens per purchase, price = display price (e.g. 'RM 9.90')
    """
    return upsert_setting(setting_key, data.setting_value, data.price)
