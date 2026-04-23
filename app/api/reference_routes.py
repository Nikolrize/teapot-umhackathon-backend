from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import ReferenceCreateRequest, ReferenceUpdateRequest
from app.services.reference_service import (
    add_reference, get_user_agent_references, update_reference, delete_reference,
)
from app.services.agent_service import get_agent
from app.services.project_service import get_session

router = APIRouter(prefix="/references")


@router.post("")
def create_reference(data: ReferenceCreateRequest):
    session = get_session(data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return add_reference(data.user_id, session["agent_id"], data.session_id, data.content)


@router.get("/user/{user_id}/agent/{agent_slug}")
def list_references(user_id: int, agent_slug: str):
    agent = get_agent(agent_slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return get_user_agent_references(user_id, agent["id"])


@router.patch("/{reference_id}")
def edit_reference(reference_id: str, data: ReferenceUpdateRequest):
    result = update_reference(reference_id, data.user_id, data.content)
    if not result:
        raise HTTPException(status_code=404, detail="Reference not found")
    return result


@router.delete("/{reference_id}")
def remove_reference(reference_id: str, user_id: int = Query(...)):
    if not delete_reference(reference_id, user_id):
        raise HTTPException(status_code=404, detail="Reference not found")
    return {"message": "Reference deleted"}
