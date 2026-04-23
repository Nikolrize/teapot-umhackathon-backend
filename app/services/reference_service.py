from app.db_connection import get_db_connection


def init_reference_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_references (
            reference_id UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id      INT     NOT NULL REFERENCES users(id),
            agent_id     INT     NOT NULL REFERENCES agents(id),
            session_id   UUID    NOT NULL REFERENCES sessions(session_id),
            content      TEXT    NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def _stringify_uuids(d: dict) -> dict:
    for key in ("reference_id", "session_id"):
        if key in d and d[key] is not None:
            d[key] = str(d[key])
    return d


def add_reference(user_id: int, agent_id: int, session_id: str, content: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agent_references (user_id, agent_id, session_id, content)
        VALUES (%s, %s, %s, %s)
        RETURNING reference_id, user_id, agent_id, session_id, content, created_at, updated_at
    """, (user_id, agent_id, session_id, content))
    result = _stringify_uuids(_row_to_dict(cur.fetchone(), cur.description))
    conn.commit()
    cur.close()
    conn.close()
    return result


def get_user_agent_references(user_id: int, agent_id: int) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT reference_id, user_id, agent_id, session_id, content, created_at, updated_at
        FROM agent_references
        WHERE user_id = %s AND agent_id = %s
        ORDER BY created_at ASC
    """, (user_id, agent_id))
    result = [_stringify_uuids(_row_to_dict(row, cur.description)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def update_reference(reference_id: str, user_id: int, content: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE agent_references
        SET content = %s, updated_at = CURRENT_TIMESTAMP
        WHERE reference_id = %s AND user_id = %s
        RETURNING reference_id, user_id, agent_id, session_id, content, created_at, updated_at
    """, (content, reference_id, user_id))
    row = cur.fetchone()
    result = _stringify_uuids(_row_to_dict(row, cur.description)) if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_reference(reference_id: str, user_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM agent_references WHERE reference_id = %s AND user_id = %s RETURNING reference_id",
        (reference_id, user_id),
    )
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted
