from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.model_service import (
    list_model_choices, list_providers,
    get_all_models, get_model, create_model, update_model, delete_model,
)

router = APIRouter(prefix="/models")


@router.get("/gemini/available")
def list_gemini_models():
    """List every Gemini model available on the configured API key."""
    from google import genai
    from app.core.config import GEMINI_API_KEY
    client = genai.Client(api_key=GEMINI_API_KEY)
    return [
        {"name": m.name, "display_name": getattr(m, "display_name", "")}
        for m in client.models.list()
    ]


class ModelCreateRequest(BaseModel):
    api_key: str
    model_provider: str
    model_choice_id: str
    token_unit: Optional[float] = None
    token_cost: Optional[float] = None


class ModelUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    model_provider: Optional[str] = None
    model_choice_id: Optional[str] = None
    token_unit: Optional[float] = None
    token_cost: Optional[float] = None


# ── Model choices (dropdown data) ─────────────────────────────────────────────

@router.get("/choices/providers")
def get_providers():
    """All distinct providers — use to populate the first dropdown."""
    return list_providers()


@router.get("/choices")
def get_all_choices():
    """All model choices regardless of provider."""
    return list_model_choices()


@router.get("/choices/{provider}")
def get_choices_by_provider(provider: str):
    """Model choices filtered by provider — use for the second dropdown."""
    return list_model_choices(provider)


# ── Model CRUD ────────────────────────────────────────────────────────────────

@router.get("")
def list_models():
    return get_all_models()


@router.get("/{model_id}")
def get_model_detail(model_id: str):
    model = get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("")
def create_model_route(data: ModelCreateRequest):
    return create_model(data.model_dump())


@router.post("/update/{model_id}")
def update_model_route(model_id: str, data: ModelUpdateRequest):
    if not get_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return update_model(model_id, data.model_dump(exclude_unset=True))


@router.post("/delete/{model_id}")
def delete_model_route(model_id: str):
    success, err, disabled_agents = delete_model(model_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Model not found")
    if err == "default":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete the default model (ilmu-glm-5.1)",
        )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete model")

    response = {"ok": True, "deleted": model_id}
    if disabled_agents:
        response["warning"] = "No model detected! Please update model before enabling these agents."
        response["disabled_agents"] = disabled_agents
    return response
