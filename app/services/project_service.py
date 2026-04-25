import uuid
from app.db_connection import get_db_connection


def init_project_tables():
    # Tables already exist in the database; nothing to create.
    pass


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(data: dict) -> dict:
    project_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects
            (project_id, user_id, project_name, project_description, business_name,
             business_type, business_context, budget_min, budget_max, goal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        project_id, data["user_id"],
        data["project_name"], data.get("project_description"),
        data["business_name"], data["business_type"], data.get("business_context"),
        data.get("budget_min"), data.get("budget_max"), data.get("goal"),
    ))
    result = _row_to_dict(cur.fetchone(), cur.description)
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_projects(user_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects WHERE user_id = %s", (str(user_id),))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def update_project(project_id: str, data: dict) -> dict | None:
    allowed = {
        "project_name", "project_description", "business_name",
        "business_type", "business_context", "budget_min", "budget_max", "goal",
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return get_project(project_id)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [project_id]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE projects SET {set_clause} WHERE project_id = %s RETURNING *", values)
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_project(project_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM projects WHERE project_id = %s RETURNING project_id", (project_id,))
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def get_project(project_id: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    cur.close()
    conn.close()
    return result


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(user_id: str, project_id: str, agent_id: str, session_name: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO session (agent_id, user_id, project_id, session_name)
        VALUES (%s, %s, %s, %s)
        RETURNING session_id, agent_id, user_id, project_id, session_name, created_at
    """, (agent_id, str(user_id), project_id, session_name))
    result = _row_to_dict(cur.fetchone(), cur.description)
    result["session_id"] = str(result["session_id"])
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_sessions(user_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.session_id, s.agent_id, s.user_id, s.project_id, s.session_name, s.created_at,
               a.agent_name,
               p.project_name
        FROM session s
        JOIN agents   a ON s.agent_id   = a.agent_id
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.user_id = %s
        ORDER BY s.created_at DESC
    """, (str(user_id),))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    for r in result:
        r["session_id"] = str(r["session_id"])
    cur.close()
    conn.close()
    return result


def delete_session(session_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM session WHERE session_id = %s RETURNING session_id",
        (session_id,),
    )
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def get_project_agent_sessions(project_id: str, agent_id: str) -> list:
    """All sessions for a specific project+agent pair — used for session switching."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.session_id, s.agent_id, s.user_id, s.project_id, s.session_name, s.created_at,
               a.agent_name
        FROM session s
        JOIN agents a ON s.agent_id = a.agent_id
        WHERE s.project_id = %s AND s.agent_id = %s
        ORDER BY s.created_at DESC
    """, (project_id, agent_id))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    for r in result:
        r["session_id"] = str(r["session_id"])
    cur.close()
    conn.close()
    return result


def get_session(session_id: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.session_id, s.agent_id, s.user_id, s.project_id, s.session_name, s.created_at,
               a.agent_name, a.model_id,
               a.requirements, a.task, a.isdisable, a.max_token, a.temperature, a.top_p,
               p.project_name, p.project_description, p.business_name,
               p.business_type, p.business_context,
               p.budget_min, p.budget_max, p.goal
        FROM session s
        JOIN agents   a ON s.agent_id   = a.agent_id
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.session_id = %s
    """, (session_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None
    result = _row_to_dict(row, cur.description)
    result["session_id"] = str(result["session_id"])
    cur.close()
    conn.close()
    return result


# ── Prompts ───────────────────────────────────────────────────────────────────

def record_message(session_id: str, content: str, content_type: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO prompt (session_id, content, content_type)
        VALUES (%s, %s, %s)
        RETURNING prompt_id, session_id, content, content_type, timestamp
    """, (session_id, content, content_type))
    result = _row_to_dict(cur.fetchone(), cur.description)
    result["prompt_id"] = str(result["prompt_id"])
    result["session_id"] = str(result["session_id"])
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_session_history(session_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT prompt_id, session_id, content, content_type, timestamp
        FROM prompt WHERE session_id = %s ORDER BY timestamp ASC
    """, (session_id,))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    for r in result:
        r["prompt_id"] = str(r["prompt_id"])
        r["session_id"] = str(r["session_id"])
    cur.close()
    conn.close()
    return result
