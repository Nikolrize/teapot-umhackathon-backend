from app.db_connection import get_db_connection


def init_project_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id   SERIAL PRIMARY KEY,
            user_id      INT NOT NULL REFERENCES users(id),
            project_name VARCHAR(200) NOT NULL,
            project_description TEXT,
            business_name VARCHAR(200) NOT NULL,
            business_type VARCHAR(100) NOT NULL,
            business_context TEXT,
            budget_min   NUMERIC(15,2),
            budget_max   NUMERIC(15,2),
            goal         TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id   INT NOT NULL REFERENCES agents(id),
            user_id    INT NOT NULL REFERENCES users(id),
            project_id INT NOT NULL REFERENCES projects(project_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            prompt_id    SERIAL PRIMARY KEY,
            session_id   UUID NOT NULL REFERENCES sessions(session_id),
            content      TEXT NOT NULL,
            content_type VARCHAR(10) NOT NULL CHECK (content_type IN ('prompt', 'reply')),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(data: dict) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO projects
            (user_id, project_name, project_description, business_name,
             business_type, business_context, budget_min, budget_max, goal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        data["user_id"], data["project_name"], data.get("project_description"),
        data["business_name"], data["business_type"], data.get("business_context"),
        data.get("budget_min"), data.get("budget_max"), data.get("goal"),
    ))
    result = _row_to_dict(cur.fetchone(), cur.description)
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_projects(user_id: int) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def get_project(project_id: int) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    cur.close()
    conn.close()
    return result


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(user_id: int, project_id: int, agent_id: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sessions (agent_id, user_id, project_id)
        VALUES (%s, %s, %s)
        RETURNING session_id, agent_id, user_id, project_id, created_at
    """, (agent_id, user_id, project_id))
    result = _row_to_dict(cur.fetchone(), cur.description)
    result["session_id"] = str(result["session_id"])
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_sessions(user_id: int) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.session_id, s.agent_id, s.user_id, s.project_id, s.created_at,
               a.name AS agent_name, a.slug AS agent_slug,
               p.project_name
        FROM sessions s
        JOIN agents   a ON s.agent_id   = a.id
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.user_id = %s
        ORDER BY s.created_at DESC
    """, (user_id,))
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
        SELECT s.session_id, s.agent_id, s.user_id, s.project_id, s.created_at,
               a.name AS agent_name, a.slug AS agent_slug,
               a.requirements, a.task, a.is_disabled, a.max_tokens, a.temperature, a.top_p,
               p.project_name, p.project_description, p.business_name,
               p.business_type, p.business_context,
               p.budget_min, p.budget_max, p.goal
        FROM sessions s
        JOIN agents   a ON s.agent_id   = a.id
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
        INSERT INTO prompts (session_id, content, content_type)
        VALUES (%s, %s, %s)
        RETURNING prompt_id, session_id, content, content_type, created_at
    """, (session_id, content, content_type))
    result = _row_to_dict(cur.fetchone(), cur.description)
    result["session_id"] = str(result["session_id"])
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_session_history(session_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT prompt_id, session_id, content, content_type, created_at
        FROM prompts WHERE session_id = %s ORDER BY created_at ASC
    """, (session_id,))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    for r in result:
        r["session_id"] = str(r["session_id"])
    cur.close()
    conn.close()
    return result
