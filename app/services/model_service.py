from app.db_connection import get_db_connection

_DEFAULT_MODEL_NAME = "ilmu-glm-5.1"


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def _stringify(d: dict) -> dict:
    for key in ("model_id", "model_choice_id"):
        if key in d and d[key] is not None:
            d[key] = str(d[key])
    return d


def _mask_key(api_key: str) -> str:
    if not api_key or len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"


def _public(d: dict) -> dict:
    """Mask the raw api_key before returning to any frontend-facing caller."""
    if "api_key" in d:
        d["api_key"] = _mask_key(d["api_key"])
    return d


# ── Internal DB fetch (raw key — never sent to the frontend) ──────────────────

def _fetch_raw(cur, model_id: str) -> dict | None:
    cur.execute("""
        SELECT m.model_id, m.api_key, m.model_provider, m.model_choice_id,
               m.token_unit, m.token_cost, mc.model_name
        FROM model m
        JOIN model_choice mc ON m.model_choice_id = mc.model_choice_id
        WHERE m.model_id = %s
    """, (model_id,))
    row = cur.fetchone()
    return _stringify(_row_to_dict(row, cur.description)) if row else None


# ── Model choices (developer-managed, read-only for admin) ────────────────────

def list_model_choices(provider: str = None) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    if provider:
        cur.execute("""
            SELECT model_choice_id, model_name, model_provider
            FROM model_choice WHERE model_provider = %s
            ORDER BY model_name
        """, (provider,))
    else:
        cur.execute("""
            SELECT model_choice_id, model_name, model_provider
            FROM model_choice ORDER BY model_provider, model_name
        """)
    result = [_stringify(_row_to_dict(row, cur.description)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def list_providers() -> list[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT model_provider FROM model_choice ORDER BY model_provider")
    result = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


# ── Model CRUD (api_key masked in all public returns) ─────────────────────────

def get_all_models() -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.model_id, m.api_key, m.model_provider, m.model_choice_id,
               m.token_unit, m.token_cost, mc.model_name
        FROM model m
        JOIN model_choice mc ON m.model_choice_id = mc.model_choice_id
        ORDER BY m.model_provider, mc.model_name
    """)
    result = [_public(_stringify(_row_to_dict(row, cur.description))) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def get_model(model_id: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    raw = _fetch_raw(cur, model_id)
    cur.close()
    conn.close()
    return _public(raw) if raw else None


def create_model(data: dict) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO model (api_key, model_provider, model_choice_id, token_unit, token_cost)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING model_id
    """, (
        data["api_key"], data["model_provider"], data["model_choice_id"],
        data.get("token_unit"), data.get("token_cost"),
    ))
    model_id = str(cur.fetchone()[0])
    conn.commit()
    raw = _fetch_raw(cur, model_id)
    cur.close()
    conn.close()
    return _public(raw)


def update_model(model_id: str, updates: dict) -> dict | None:
    allowed = {"api_key", "model_provider", "model_choice_id", "token_unit", "token_cost"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return get_model(model_id)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [model_id]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE model SET {set_clause} WHERE model_id = %s RETURNING model_id", values)
    updated = cur.fetchone()
    conn.commit()
    raw = _fetch_raw(cur, model_id) if updated else None
    cur.close()
    conn.close()
    return _public(raw) if raw else None


def delete_model(model_id: str) -> tuple[bool, str | None, list]:
    """
    Returns (success, error_reason, disabled_agents).
    After deletion the DB FK (ON DELETE SET NULL) nullifies agents.model_id.
    Any custom agent left with model_id = NULL is then auto-disabled here.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT mc.model_name FROM model m
        JOIN model_choice mc ON m.model_choice_id = mc.model_choice_id
        WHERE m.model_id = %s
    """, (model_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return False, "not_found", []
    if row[0] == _DEFAULT_MODEL_NAME:
        cur.close()
        conn.close()
        return False, "default", []

    cur.execute("DELETE FROM model WHERE model_id = %s RETURNING model_id", (model_id,))
    if not cur.fetchone():
        conn.rollback()
        cur.close()
        conn.close()
        return False, None, []

    # Auto-disable every custom agent whose model_id was just nullified by the FK cascade
    cur.execute("""
        UPDATE agents SET isdisable = true
        WHERE type = 'custom' AND model_id IS NULL AND isdisable = false
        RETURNING agent_id, agent_name
    """)
    disabled_agents = [
        {"agent_id": r[0], "agent_name": r[1]} for r in cur.fetchall()
    ]
    conn.commit()
    cur.close()
    conn.close()
    return True, None, disabled_agents


# ── Agent model resolution (internal only) ────────────────────────────────────

def resolve_agent_model(model_id: str | None) -> dict | None:
    """
    Returns {"api_key", "model_name", "model_provider"} for the agent's assigned model.
    model_provider is used by glm_service to look up base_url from PROVIDER_BASE_URLS.
    Returns None → caller falls back to system defaults from .env.
    Never returned to any frontend route.
    """
    if not model_id:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    raw = _fetch_raw(cur, str(model_id))
    cur.close()
    conn.close()
    if not raw:
        return None
    return {
        "api_key":        raw["api_key"],
        "model_name":     raw["model_name"],
        "model_provider": raw["model_provider"],
    }
