from datetime import datetime, timezone
from app.db_connection import get_db_connection


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


# ── System settings ────────────────────────────────────────────────────────────

def init_settings_table() -> None:
    """Add the `name` column to system_settings if it doesn't exist yet."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE system_settings
        ADD COLUMN IF NOT EXISTS name VARCHAR(255)
    """)
    conn.commit()
    cur.close()
    conn.close()


def get_all_settings() -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT setting_key, setting_value, price, name FROM system_settings ORDER BY setting_key"
    )
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result


def get_setting(key: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT setting_key, setting_value, price, name FROM system_settings WHERE setting_key = %s",
        (key,),
    )
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    cur.close()
    conn.close()
    return result


def upsert_setting(key: str, value: int, price: str | None = None, name: str | None = None) -> dict:
    """Create or update a system setting. Existing name is preserved when name is not provided."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO system_settings (setting_key, setting_value, price, name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                price         = EXCLUDED.price,
                name          = COALESCE(EXCLUDED.name, system_settings.name)
        RETURNING setting_key, setting_value, price, name
    """, (key, value, price, name))
    result = _row_to_dict(cur.fetchone(), cur.description)
    conn.commit()
    cur.close()
    conn.close()
    return result


# ── Purchase ───────────────────────────────────────────────────────────────────

def process_purchase(user_id: str, purchase_type: str = "token") -> dict:
    """
    MVP purchase flow (no payment gateway).
    Looks up the token_pack setting, records the purchase, and credits
    the user's purchased_token_remaining.
    """
    setting = get_setting("token_pack")
    if not setting:
        raise ValueError("Token pack not configured. Please ask admin to set it up.")

    tokens_to_add = setting["setting_value"]
    price         = setting["price"] or "N/A"

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO purchase (purchase_type, user_id, payment, purchase_on)
        VALUES (%s, %s, %s, %s)
        RETURNING purchase_id, purchase_type, user_id, payment, purchase_on
    """, (purchase_type, user_id, price, datetime.now(timezone.utc)))
    purchase = _row_to_dict(cur.fetchone(), cur.description)
    purchase["purchase_id"] = str(purchase["purchase_id"])

    cur.execute("""
        UPDATE users
        SET purchased_token_remaining = COALESCE(purchased_token_remaining, 0) + %s
        WHERE user_id = %s
        RETURNING purchased_token_remaining
    """, (tokens_to_add, user_id))
    row = cur.fetchone()
    if not row:
        conn.rollback()
        cur.close()
        conn.close()
        raise ValueError("User not found")

    conn.commit()
    cur.close()
    conn.close()

    return {
        "purchase":                  purchase,
        "tokens_added":              tokens_to_add,
        "purchased_token_remaining": row[0],
        "price":                     price,
    }


def get_purchase_history(user_id: str) -> list:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT purchase_id, purchase_type, user_id, payment, purchase_on
        FROM purchase
        WHERE user_id = %s
        ORDER BY purchase_on DESC
    """, (user_id,))
    result = [_row_to_dict(row, cur.description) for row in cur.fetchall()]
    for r in result:
        r["purchase_id"] = str(r["purchase_id"])
    cur.close()
    conn.close()
    return result
