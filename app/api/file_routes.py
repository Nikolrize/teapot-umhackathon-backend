from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.services.file_service import process_file
from app.services.project_service import get_session, record_message

router = APIRouter(prefix="/sessions")

_MAX_FILE_MB = 20
_MAX_BYTES = _MAX_FILE_MB * 1024 * 1024


@router.post("/{session_id}/upload-chat")
async def upload_to_chat(
    session_id: str,
    file: UploadFile = File(...),
    message: str = Form(default=""),
):
    """
    Upload a PDF or CSV and inject its content into the session history as a
    user message. The user can then ask follow-up questions via the normal
    POST /sessions/{session_id}/chat endpoint.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{session['agent_name']}' is currently disabled")

    content_type = file.content_type or ""
    if not any(t in content_type for t in ("pdf", "csv")) and \
       not file.filename.lower().endswith((".pdf", ".csv")):
        raise HTTPException(status_code=415, detail="Only PDF and CSV files are supported")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_MB} MB limit")

    try:
        extracted = process_file(file_bytes, file.filename, content_type)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"File processing failed: {e}")

    user_text = f"{message}\n\n" if message.strip() else ""
    stored_message = (
        f"{user_text}"
        f"--- Uploaded file: {file.filename} ---\n"
        f"{extracted}\n"
        f"--- End of file content ---"
    )

    record_message(session_id, stored_message, "prompt")

    return {
        "filename": file.filename,
        "extracted_summary": extracted,
        "message": "File added to conversation. You can now ask questions about it.",
    }
