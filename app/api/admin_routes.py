from fastapi import APIRouter, HTTPException
from app.models.schemas import AgentUpdateRequest, AgentCreateRequest
from app.services.agent_service import get_all_agents, get_agent, update_agent, create_agent, delete_agent
from app.services.model_service import get_model, get_all_models

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


@router.patch("/{agent_id}")
def update_agent_route(agent_id: str, data: AgentUpdateRequest):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = data.model_dump(exclude_unset=True)

    # Block re-enabling a custom agent that has no model assigned
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


@router.delete("/{agent_id}")
def delete_custom_agent(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["type"] == "default":
        raise HTTPException(status_code=403, detail="Default agents cannot be deleted")
    if not delete_agent(agent_id):
        raise HTTPException(status_code=500, detail="Failed to delete agent")
    return {"message": f"Agent '{agent_id}' deleted"}
