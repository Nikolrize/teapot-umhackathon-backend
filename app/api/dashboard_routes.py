from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.dashboard_service import (
    get_or_create_dashboard,
    get_dashboard_with_content,
    add_content,
    update_content,
    delete_content,
)
from app.services.project_service import get_project

router = APIRouter(prefix="/dashboard")


class AddContentRequest(BaseModel):
    user_id: str
    prompt_id: str
    content: str


class UpdateContentRequest(BaseModel):
    content: str


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/{project_id}")
def get_dashboard(project_id: str):
    """Get the dashboard for a project. Auto-creates one if it doesn't exist yet."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dashboard = get_or_create_dashboard(project["user_id"], project_id)
    result = get_dashboard_with_content(project_id)
    return result if result else {**dashboard, "content": []}


# ── Dashboard content ──────────────────────────────────────────────────────────

@router.post("/{project_id}/add")
def add_to_dashboard(project_id: str, data: AddContentRequest):
    """Pin an agent response to this project's dashboard."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dashboard = get_or_create_dashboard(data.user_id, project_id)
    return add_content(dashboard["dashboard_id"], data.prompt_id, data.content)


@router.post("/content/{content_id}/update")
def update_dashboard_content(content_id: str, data: UpdateContentRequest):
    """Edit the text of a pinned dashboard item."""
    result = update_content(content_id, data.content)
    if not result:
        raise HTTPException(status_code=404, detail="Content item not found")
    return result


@router.post("/content/{content_id}/delete")
def delete_dashboard_content(content_id: str):
    """Remove a pinned item from the dashboard."""
    if not delete_content(content_id):
        raise HTTPException(status_code=404, detail="Content item not found")
    return {"ok": True, "deleted": content_id}
