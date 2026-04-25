import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.services.project_service import get_session
from app.services.reference_service import get_user_agent_references
from app.services.model_service import resolve_agent_model
from app.services.generation_service import generate_document

router = APIRouter(prefix="/sessions")

_SUPPORTED_TYPES = ("pdf", "ppt", "csv")


class GenerateRequest(BaseModel):
    document_type: str          # "pdf" | "ppt" | "csv"
    topic: Optional[str] = None # defaults to the agent's own task if omitted


@router.post("/{session_id}/generate")
def generate_report(session_id: str, data: GenerateRequest):
    """
    Generate a professional PDF, PPT, or CSV from the current session context.
    The agent's role, project details, and any stored references are all
    automatically injected into the prompt.
    """
    if data.document_type not in _SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"document_type must be one of: {', '.join(_SUPPORTED_TYPES)}",
        )

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["isdisable"]:
        raise HTTPException(
            status_code=403,
            detail=f"Agent '{session['agent_name']}' is currently disabled",
        )

    references = get_user_agent_references(session["user_id"], session["agent_id"])
    model      = resolve_agent_model(session.get("model_id"))

    try:
        file_bytes, filename, mime = generate_document(
            session, references, data.topic, data.document_type, model
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {e}")

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
