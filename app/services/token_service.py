from datetime import datetime, timezone, timedelta
from app.db_connection import get_db_connection

_REFRESH_HOURS = 5  # Token quota resets every 5 hours from first message


def _get_token_info(user_id: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, token_used, max_token,
               COALESCE(purchased_token_remaining, 0) AS purchased_token_remaining,
               token_refresh_at
        FROM users WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "user_id":                   row[0],
        "token_used":                row[1],
        "max_token":                 row[2],
        "purchased_token_remaining": row[3],
        "token_refresh_at":          row[4],
    }


def _server_now() -> datetime:
    """Always use server UTC time — never trust client-side timestamps."""
    return datetime.now(timezone.utc)


def _make_aware(dt) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check_and_refresh(user_id: str) -> dict:
    """
    Called before every LLM request.

    - If token_refresh_at is NULL (user's first ever message):
        → set token_refresh_at = now + 5 hours  (starts the clock)

    - If token_refresh_at has passed:
        → reset token_used = 0
        → set token_refresh_at = now + 5 hours  (roll forward)

    Uses server UTC time exclusively.
    """
    info = _get_token_info(user_id)
    if not info:
        return {}

    now        = _server_now()
    refresh_at = _make_aware(info["token_refresh_at"])
    next_refresh = now + timedelta(hours=_REFRESH_HOURS)

    conn = get_db_connection()
    cur  = conn.cursor()

    if refresh_at is None:
        # First message — initialise the 5-hour window
        cur.execute(
            "UPDATE users SET token_refresh_at = %s WHERE user_id = %s",
            (next_refresh, user_id),
        )
        conn.commit()
        info["token_refresh_at"] = next_refresh

    elif refresh_at <= now:
        # Window expired — reset counter and open a new 5-hour window
        cur.execute(
            "UPDATE users SET token_used = 0, token_refresh_at = %s WHERE user_id = %s",
            (next_refresh, user_id),
        )
        conn.commit()
        info["token_used"]       = 0
        info["token_refresh_at"] = next_refresh

    cur.close()
    conn.close()
    return info


def is_within_limit(info: dict) -> bool:
    """True if the user still has tokens available (free + purchased)."""
    total = info["max_token"] + info["purchased_token_remaining"]
    return info["token_used"] < total


def consume_tokens(user_id: str, tokens: int) -> None:
    """
    Increment token_used by `tokens`.
    Once token_used exceeds max_token, the overflow is deducted from
    purchased_token_remaining (floored at 0).
    Always consumes at least 1 token so the counter always moves.
    """
    tokens = max(tokens, 1)

    info = _get_token_info(user_id)
    if not info:
        return

    new_used = info["token_used"] + tokens

    if info["token_used"] >= info["max_token"]:
        deduct = tokens                       # already past free tier
    elif new_used > info["max_token"]:
        deduct = new_used - info["max_token"] # partial overflow
    else:
        deduct = 0                            # still within free tier

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE users
        SET token_used = %s,
            purchased_token_remaining = GREATEST(
                COALESCE(purchased_token_remaining, 0) - %s, 0
            )
        WHERE user_id = %s
    """, (new_used, deduct, user_id))
    conn.commit()
    cur.close()
    conn.close()


def get_token_status(user_id: str) -> dict | None:
    """Return a clean token summary for the frontend."""
    info = check_and_refresh(user_id)
    if not info:
        return None
    total_available = info["max_token"] + info["purchased_token_remaining"]
    return {
        "user_id":                   user_id,
        "token_used":                info["token_used"],
        "max_token":                 info["max_token"],
        "purchased_token_remaining": info["purchased_token_remaining"],
        "total_available":           total_available,
        "tokens_remaining":          max(total_available - info["token_used"], 0),
        "token_refresh_at":          info["token_refresh_at"],
    }
