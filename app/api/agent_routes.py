from fastapi import APIRouter, HTTPException
from app.models.schemas import WorkspaceContext
from app.services.agent_service import get_agent
from app.services.glm_service import call_glm

router = APIRouter(prefix="/agents")


@router.post("/{agent_id}")
def run_agent(agent_id: str, data: WorkspaceContext):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{agent['agent_name']}' is currently disabled")
    context = {
        "task": agent["task"],
        "business": data.model_dump(),
    }
    return call_glm(agent["max_token"], agent["requirements"], context, agent["temperature"], agent["top_p"])
