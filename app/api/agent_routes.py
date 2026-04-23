from fastapi import APIRouter, HTTPException
from app.models.schemas import WorkspaceContext
from app.services.agent_service import get_agent
from app.services.glm_service import call_glm

router = APIRouter(prefix="/agents")


@router.post("/{slug}")
def run_agent(slug: str, data: WorkspaceContext):
    agent = get_agent(slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["is_disabled"]:
        raise HTTPException(status_code=403, detail=f"Agent '{agent['name']}' is currently disabled")
    context = {
        "task": agent["task"],
        "business": data.model_dump(),
    }
    return call_glm(agent["max_tokens"], agent["requirements"], context, agent["temperature"], agent["top_p"])