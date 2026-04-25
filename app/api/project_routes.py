from fastapi import APIRouter, HTTPException
from app.models.schemas import ProjectCreateRequest, ProjectUpdateRequest, SessionCreateRequest, ChatRequest
from app.services.project_service import (
    create_project, get_user_projects, get_project, update_project, delete_project,
    create_session, get_user_sessions, get_session, get_project_agent_sessions, delete_session,
    record_message, get_session_history,
)
from app.services.agent_service import get_agent
from app.services.reference_service import get_user_agent_references
from app.services.glm_service import call_glm_session
from app.services.model_service import resolve_agent_model
from app.services.token_service import check_and_refresh, is_within_limit, consume_tokens

router = APIRouter()


def _build_system_prompt(session: dict, references: list) -> str:
    base = (
        f"{session['requirements']}\n\n"
        f"Project Context:\n"
        f"- Project: {session['project_name']}\n"
        f"- Description: {session['project_description'] or 'n/a'}\n"
        f"- Business: {session['business_name']} ({session['business_type']})\n"
        f"- Context: {session['business_context'] or 'n/a'}\n"
        f"- Budget: {session['budget_min'] or 'n/a'} – {session['budget_max'] or 'n/a'}\n"
        f"- Goal: {session['goal'] or 'n/a'}\n\n"
    )
    if references:
        ref_block = "\n".join(f"- {r['content']}" for r in references)
        base += (
            f"References (established facts to draw from):\n{ref_block}\n\n"
            f"Important: Do not repeat or rephrase content already covered in the references above.\n\n"
        )
    return base + f"Your task: {session['task']}"


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/projects")
def create_project_route(data: ProjectCreateRequest):
    return create_project(data.model_dump())


@router.get("/projects/user/{user_id}")
def list_user_projects(user_id: str):
    return get_user_projects(user_id)


@router.get("/projects/{project_id}")
def get_project_route(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/update/{project_id}")
def update_project_route(project_id: str, data: ProjectUpdateRequest):
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return update_project(project_id, data.model_dump(exclude_unset=True))


@router.post("/projects/delete/{project_id}")
def delete_project_route(project_id: str):
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not delete_project(project_id):
        raise HTTPException(status_code=500, detail="Failed to delete project")
    return {"ok": True, "deleted": project_id}


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.post("/sessions")
def create_session_route(data: SessionCreateRequest):
    if not get_project(data.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    agent = get_agent(data.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{agent['agent_name']}' is currently disabled")
    session = create_session(data.user_id, data.project_id, agent["agent_id"], data.session_name)
    if agent.get("conversation_starter"):
        record_message(session["session_id"], agent["conversation_starter"], "reply")
    return session


@router.get("/sessions/user/{user_id}")
def list_user_sessions(user_id: str):
    return get_user_sessions(user_id)


@router.get("/sessions/{session_id}")
def get_session_route(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session, "history": get_session_history(session_id)}


@router.post("/sessions/delete/{session_id}")
def delete_session_route(session_id: str):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    if not delete_session(session_id):
        raise HTTPException(status_code=500, detail="Failed to delete session")
    return {"ok": True, "deleted": session_id}


@router.get("/sessions/switch/{project_id}/{agent_id}")
def list_switchable_sessions(project_id: str, agent_id: str):
    """
    List all sessions for a project+agent pair so the client can switch between
    existing ones or decide to open a new one via POST /sessions.
    """
    return get_project_agent_sessions(project_id, agent_id)


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/chat")
def chat(session_id: str, data: ChatRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["isdisable"]:
        raise HTTPException(status_code=403, detail=f"Agent '{session['agent_name']}' is currently disabled")

    references = get_user_agent_references(session["user_id"], session["agent_id"])
    history    = get_session_history(session_id)

    window  = 2 if references else 6
    recent  = history[-window:]

    while recent and recent[0]["content_type"] == "reply":
        recent = recent[1:]

    messages = [
        {"role": "user" if msg["content_type"] == "prompt" else "assistant", "content": msg["content"]}
        for msg in recent
    ]
    messages.append({"role": "user", "content": data.message})

    system_prompt = _build_system_prompt(session, references)
    model = resolve_agent_model(session.get("model_id"))

    # ── Token gate ─────────────────────────────────────────────────────────────
    token_info = check_and_refresh(session["user_id"])
    if not is_within_limit(token_info):
        raise HTTPException(
            status_code=402,
            detail="Token limit reached. Please purchase more tokens to continue.",
        )

    record_message(session_id, data.message, "prompt")
    reply, tokens_used = call_glm_session(
        session["max_token"], system_prompt, messages,
        session["temperature"], session["top_p"],
        api_key=model["api_key"] if model else None,
        model_name=model["model_name"] if model else None,
        model_provider=model["model_provider"] if model else None,
    )
    record_message(session_id, reply, "reply")
    consume_tokens(session["user_id"], tokens_used)

    return {"reply": reply}
