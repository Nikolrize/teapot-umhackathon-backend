from app.db_connection import get_db_connection


def init_reference_table():
    # Table already exists in the database; nothing to create.
    pass


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def _stringify_uuids(d: dict) -> dict:
    for key in ("reference_id", "session_id"):
        if key in d and d[key] is not None:
            d[key] = str(d[key])
    return d


def add_reference(user_id: str, agent_id: str, session_id: str, content: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reference (user_id, agent_id, session_id, content)
        VALUES (%s, %s, %s, %s)
        RETURNING reference_id, user_id, agent_id, session_id, content
    """, (str(user_id), agent_id, session_id, content))
    result = _stringify_uuids(_row_to_dict(cur.fetchone(), cur.description))
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_agent_references(user_id: str, agent_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT reference_id, user_id, agent_id, session_id, content
        FROM reference
        WHERE user_id = %s AND agent_id = %s
    """, (str(user_id), agent_id))
    result = [_stringify_uuids(_row_to_dict(row, cur.description)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def update_reference(reference_id: str, user_id: str, content: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE reference
        SET content = %s
        WHERE reference_id = %s AND user_id = %s
        RETURNING reference_id, user_id, agent_id, session_id, content
    """, (content, reference_id, str(user_id)))
    row = cur.fetchone()
    result = _stringify_uuids(_row_to_dict(row, cur.description)) if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_reference(reference_id: str, user_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM reference WHERE reference_id = %s AND user_id = %s RETURNING reference_id",
        (reference_id, str(user_id)),
    )
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted
