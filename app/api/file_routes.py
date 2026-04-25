from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.services.file_service import process_file
from app.services.project_service import get_session, record_message, get_session_history
from app.services.reference_service import get_user_agent_references
from app.services.glm_service import call_glm_session
from app.services.model_service import resolve_agent_model
from app.services.token_service import check_and_refresh, is_within_limit, consume_tokens

router = APIRouter(prefix="/sessions")

_MAX_FILE_MB = 20
_MAX_BYTES = _MAX_FILE_MB * 1024 * 1024


@router.post("/{session_id}/upload-chat")
async def upload_and_chat(
    session_id: str,
    file: UploadFile = File(...),
    message: str = Form(default="Analyse this file and provide business insights."),
):
    """
    Upload a PDF or CSV, extract its content via Gemini, inject it into
    the agent prompt, and return the agent's reply — all in one call.
    """
    # ── Validate session ───────────────────────────────────────────────────────
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{session['agent_name']}' is currently disabled")

    # ── Validate file ──────────────────────────────────────────────────────────
    content_type = file.content_type or ""
    if not any(t in content_type for t in ("pdf", "csv")) and \
       not file.filename.lower().endswith((".pdf", ".csv")):
        raise HTTPException(status_code=415, detail="Only PDF and CSV files are supported")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_MB} MB limit")

    # ── Extract file content via Gemini ────────────────────────────────────────
    try:
        extracted = process_file(file_bytes, file.filename, content_type)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"File processing failed: {e}")

    # ── Build enriched user message ────────────────────────────────────────────
    enriched_message = (
        f"{message}\n\n"
        f"--- Uploaded file: {file.filename} ---\n"
        f"{extracted}\n"
        f"--- End of file content ---"
    )

    # ── Fetch references and recent history ────────────────────────────────────
    references = get_user_agent_references(session["user_id"], session["agent_id"])
    history    = get_session_history(session_id)

    window = 2 if references else 6
    recent = history[-window:]
    while recent and recent[0]["content_type"] == "reply":
        recent = recent[1:]

    messages = [
        {"role": "user" if m["content_type"] == "prompt" else "assistant", "content": m["content"]}
        for m in recent
    ]
    messages.append({"role": "user", "content": enriched_message})

    # ── Build system prompt (same logic as normal chat) ────────────────────────
    base = (
        f"{session['requirements']}\n\n"
        f"Project Context:\n"
        f"- Project: {session['project_name']}\n"
        f"- Business: {session['business_name']} ({session['business_type']})\n"
        f"- Context: {session['business_context'] or 'n/a'}\n"
        f"- Budget: {session['budget_min'] or 'n/a'} – {session['budget_max'] or 'n/a'}\n"
        f"- Goal: {session['goal'] or 'n/a'}\n\n"
    )
    if references:
        ref_block = "\n".join(f"- {r['content']}" for r in references)
        base += f"References:\n{ref_block}\n\n"
    system_prompt = base + f"Your task: {session['task']}"

    # ── Token gate ─────────────────────────────────────────────────────────────
    model = resolve_agent_model(session.get("model_id"))
    token_info = check_and_refresh(session["user_id"])
    if not is_within_limit(token_info):
        raise HTTPException(
            status_code=402,
            detail="Token limit reached. Please purchase more tokens to continue.",
        )

    record_message(session_id, enriched_message, "prompt")
    reply, tokens_used = call_glm_session(
        session["max_token"], system_prompt, messages,
        session["temperature"], session["top_p"],
        api_key=model["api_key"] if model else None,
        model_name=model["model_name"] if model else None,
        model_provider=model["model_provider"] if model else None,
    )
    record_message(session_id, reply, "reply")
    consume_tokens(session["user_id"], tokens_used)

    return {
        "filename": file.filename,
        "extracted_summary": extracted,
        "reply": reply,
    }
