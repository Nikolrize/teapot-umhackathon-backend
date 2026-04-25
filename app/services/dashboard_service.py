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
    # New item always goes to the end; index starts at 1
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


def reorder_content(content_id: str, new_index: int) -> dict | None:
    """
    Move a content item to new_index and shift all neighbours to stay contiguous.
    Index is always clamped to [1, total_items] — the frontend never needs to
    validate the range itself.

    Moving index 6 → 1:  items at 1,2,3,4,5 shift to 2,3,4,5,6  (shift +1)
    Moving index 2 → 5:  items at 3,4,5     shift to 2,3,4       (shift -1)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch current position and dashboard
    cur.execute(
        "SELECT dashboard_id, index FROM dashboard_content WHERE content_id = %s",
        (content_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None

    dashboard_id, old_index = row

    # Total items = upper bound for new_index
    cur.execute(
        "SELECT COUNT(*) FROM dashboard_content WHERE dashboard_id = %s",
        (dashboard_id,),
    )
    total = cur.fetchone()[0]

    # Clamp new_index to valid range
    new_index = max(1, min(new_index, total))

    if old_index == new_index:
        # Nothing to do — return current state
        cur.execute("""
            SELECT content_id, prompt_id, dashboard_id, content, index
            FROM dashboard_content WHERE content_id = %s
        """, (content_id,))
        result = _stringify(_row_to_dict(cur.fetchone(), cur.description))
        cur.close()
        conn.close()
        return result

    if new_index < old_index:
        # Moving to a lower index → push everything in [new_index, old_index-1] up by 1
        cur.execute("""
            UPDATE dashboard_content
            SET index = index + 1
            WHERE dashboard_id = %s
              AND index >= %s AND index < %s
              AND content_id != %s
        """, (dashboard_id, new_index, old_index, content_id))
    else:
        # Moving to a higher index → pull everything in [old_index+1, new_index] down by 1
        cur.execute("""
            UPDATE dashboard_content
            SET index = index - 1
            WHERE dashboard_id = %s
              AND index > %s AND index <= %s
              AND content_id != %s
        """, (dashboard_id, old_index, new_index, content_id))

    # Place the moved item at its target
    cur.execute("""
        UPDATE dashboard_content SET index = %s WHERE content_id = %s
        RETURNING content_id, prompt_id, dashboard_id, content, index
    """, (new_index, content_id))
    result = _stringify(_row_to_dict(cur.fetchone(), cur.description))
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_content(content_id: str) -> bool:
    """
    Delete a content item and close the gap by shifting all items
    that came after it down by 1, keeping the sequence contiguous.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Need the dashboard_id and index before deleting
    cur.execute(
        "SELECT dashboard_id, index FROM dashboard_content WHERE content_id = %s",
        (content_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return False

    dashboard_id, deleted_index = row

    cur.execute("DELETE FROM dashboard_content WHERE content_id = %s", (content_id,))

    # Close the gap — everything above the deleted item shifts down by 1
    cur.execute("""
        UPDATE dashboard_content
        SET index = index - 1
        WHERE dashboard_id = %s AND index > %s
    """, (dashboard_id, deleted_index))

    conn.commit()
    cur.close()
    conn.close()
    return True
