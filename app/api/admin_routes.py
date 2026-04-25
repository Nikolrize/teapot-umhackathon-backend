from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.schemas import AgentUpdateRequest, AgentCreateRequest
from app.services.agent_service import get_all_agents, get_agent, update_agent, create_agent, delete_agent
from app.services.model_service import get_model, get_all_models
from app.services.project_service import create_project, create_session, record_message

router = APIRouter(prefix="/agents")


@router.get("")
def list_agents():
    return get_all_agents()


@router.get("/{agent_id}")
def get_agent_detail(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/update/{agent_id}")
def update_agent_route(agent_id: str, data: AgentUpdateRequest):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = data.model_dump(exclude_unset=True)

    if updates.get("isdisable") is False and agent["type"] == "custom" and not agent.get("model_id"):
        raise HTTPException(
            status_code=400,
            detail="No model detected! Please update model before enabling the agent.",
        )

    return update_agent(agent_id, updates)


@router.get("/available-models")
def list_available_models():
    """Returns all configured models for the model_id dropdown when creating an agent."""
    return get_all_models()


@router.post("")
def create_custom_agent(data: AgentCreateRequest):
    if data.model_id and not get_model(data.model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return create_agent(data.model_dump())


@router.post("/delete/{agent_id}")
def delete_custom_agent(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["type"] == "default":
        raise HTTPException(status_code=403, detail="Default agents cannot be deleted")
    if not delete_agent(agent_id):
        raise HTTPException(status_code=500, detail="Failed to delete agent")
    return {"message": f"Agent '{agent_id}' deleted"}


# ── Admin preview ──────────────────────────────────────────────────────────────

class PreviewRequest(BaseModel):
    user_id: str
    business_name: str
    business_type: str
    business_context: Optional[str] = None


@router.post("/{agent_id}/preview")
def start_preview_session(agent_id: str, data: PreviewRequest):
    """
    Create a lightweight preview session so the admin can test an agent
    exactly as a client would — conversation_starter included.
    Returns a session_id the admin then uses with POST /client/sessions/{session_id}/chat.
    """
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{agent['agent_name']}' is currently disabled")

    # Create a temporary preview project
    project = create_project({
        "user_id": data.user_id,
        "project_name": f"[Preview] {agent['agent_name']}",
        "business_name": data.business_name,
        "business_type": data.business_type,
        "business_context": data.business_context or "",
        "budget_min": None,
        "budget_max": None,
        "goal": "Admin preview session",
    })

    session = create_session(
        data.user_id,
        project["project_id"],
        agent_id,
        f"Preview — {agent['agent_name']}",
    )

    # Insert conversation_starter as first reply if set
    if agent.get("conversation_starter"):
        record_message(session["session_id"], agent["conversation_starter"], "reply")

    return {
        "session_id": session["session_id"],
        "project_id": project["project_id"],
        "agent_name": agent["agent_name"],
        "conversation_starter": agent.get("conversation_starter"),
    }
