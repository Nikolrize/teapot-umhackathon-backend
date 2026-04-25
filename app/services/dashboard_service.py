from app.db_connection import get_db_connection


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def _stringify(d: dict) -> dict:
    for key in ("dashboard_id", "content_id", "prompt_id"):
        if key in d and d[key] is not None:
            d[key] = str(d[key])
    return d


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_or_create_dashboard(user_id: str, project_id: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT dashboard_id, user_id, project_id FROM dashboard WHERE project_id = %s",
        (project_id,),
    )
    row = cur.fetchone()
    if row:
        result = _stringify(_row_to_dict(row, cur.description))
        cur.close()
        conn.close()
        return result

    cur.execute("""
        INSERT INTO dashboard (user_id, project_id)
        VALUES (%s, %s)
        RETURNING dashboard_id, user_id, project_id
    """, (str(user_id), project_id))
    result = _stringify(_row_to_dict(cur.fetchone(), cur.description))
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_dashboard_with_content(project_id: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT dashboard_id, user_id, project_id FROM dashboard WHERE project_id = %s",
        (project_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None
    dashboard = _stringify(_row_to_dict(row, cur.description))

    cur.execute("""
        SELECT content_id, prompt_id, dashboard_id, content, index
        FROM dashboard_content
        WHERE dashboard_id = %s
        ORDER BY index ASC
    """, (dashboard["dashboard_id"],))
    items = [_stringify(_row_to_dict(r, cur.description)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return {**dashboard, "content": items}


# ── Dashboard content ──────────────────────────────────────────────────────────

def add_content(dashboard_id: str, prompt_id: str, content: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    # Auto-assign the next index
    cur.execute(
        "SELECT COALESCE(MAX(index), 0) + 1 FROM dashboard_content WHERE dashboard_id = %s",
        (dashboard_id,),
    )
    next_index = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO dashboard_content (prompt_id, dashboard_id, content, index)
        VALUES (%s, %s, %s, %s)
        RETURNING content_id, prompt_id, dashboard_id, content, index
    """, (prompt_id, dashboard_id, content, next_index))
    result = _stringify(_row_to_dict(cur.fetchone(), cur.description))
    conn.commit()
    cur.close()
    conn.close()
    return result


def update_content(content_id: str, content: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE dashboard_content
        SET content = %s
        WHERE content_id = %s
        RETURNING content_id, prompt_id, dashboard_id, content, index
    """, (content, content_id))
    row = cur.fetchone()
    result = _stringify(_row_to_dict(row, cur.description)) if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_content(content_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM dashboard_content WHERE content_id = %s RETURNING content_id",
        (content_id,),
    )
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted
