from fastapi import APIRouter, HTTPException
from app.models.schemas import ProjectCreateRequest, SessionCreateRequest, ChatRequest
from app.services.project_service import (
    create_project, get_user_projects, get_project,
    create_session, get_user_sessions, get_session,
    record_message, get_session_history,
)
from app.services.agent_service import get_agent
from app.services.reference_service import get_user_agent_references
from app.services.glm_service import call_glm_session

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
def list_user_projects(user_id: int):
    return get_user_projects(user_id)


@router.get("/projects/{project_id}")
def get_project_route(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.post("/sessions")
def create_session_route(data: SessionCreateRequest):
    if not get_project(data.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    agent = get_agent(data.agent_slug)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["is_disabled"]:
        raise HTTPException(status_code=403, detail=f"Agent '{agent['name']}' is currently disabled")
    return create_session(data.user_id, data.project_id, agent["id"])


@router.get("/sessions/user/{user_id}")
def list_user_sessions(user_id: int):
    return get_user_sessions(user_id)


@router.get("/sessions/{session_id}")
def get_session_route(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session, "history": get_session_history(session_id)}


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/chat")
def chat(session_id: str, data: ChatRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["is_disabled"]:
        raise HTTPException(status_code=403, detail=f"Agent '{session['agent_name']}' is currently disabled")

    references = get_user_agent_references(session["user_id"], session["agent_id"])
    history    = get_session_history(session_id)

    # With references: carry last 1 pair (2 msgs) for context
    # Without references: carry last 3 pairs (6 msgs) for context
    window   = 2 if references else 6
    recent   = history[-window:]

    # Guard: Anthropic requires messages to start with role=user
    while recent and recent[0]["content_type"] == "reply":
        recent = recent[1:]

    messages = [
        {"role": "user" if msg["content_type"] == "prompt" else "assistant", "content": msg["content"]}
        for msg in recent
    ]
    messages.append({"role": "user", "content": data.message})

    system_prompt = _build_system_prompt(session, references)

    record_message(session_id, data.message, "prompt")
    reply = call_glm_session(session["max_tokens"], system_prompt, messages, session["temperature"], session["top_p"])
    record_message(session_id, reply, "reply")

    return {"reply": reply}
