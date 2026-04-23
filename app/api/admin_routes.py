from fastapi import APIRouter, HTTPException
from app.models.schemas import AgentUpdateRequest, AgentCreateRequest
from app.services.agent_service import get_all_agents, get_agent, update_agent, create_agent, delete_agent

router = APIRouter(prefix="/agents")


@router.get("")
def list_agents():
    return get_all_agents()


@router.get("/{slug}")
def get_agent_detail(slug: str):
    agent = get_agent(slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{slug}")
def update_agent_route(slug: str, data: AgentUpdateRequest):
    agent = get_agent(slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return update_agent(slug, data.dict(exclude_none=True))


@router.post("")
def create_custom_agent(data: AgentCreateRequest):
    if get_agent(data.slug):
        raise HTTPException(status_code=409, detail="Agent with this slug already exists")
    return create_agent(data.dict())


@router.delete("/{slug}")
def delete_custom_agent(slug: str):
    agent = get_agent(slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["type"] == "default":
        raise HTTPException(status_code=403, detail="Default agents cannot be deleted")
    if not delete_agent(slug):
        raise HTTPException(status_code=500, detail="Failed to delete agent")
    return {"message": f"Agent '{slug}' deleted"}