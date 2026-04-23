from app.db_connection import get_db_connection

DEFAULT_AGENTS = [
    {
        "slug": "sales-predictor",
        "name": "Sales Predictor",
        "task": "Predict future sales trends and revenue opportunities.",
        "requirements": "You are a sales analyst with over 10 years of experience forecasting revenue trends and identifying growth opportunities for businesses.",
    },
    {
        "slug": "pain-point-analyzer",
        "name": "Pain Point Analyzer",
        "task": "Identify the key pain points and operational challenges facing the business.",
        "requirements": "You are an operations consultant with over 10 years of experience diagnosing business inefficiencies and operational challenges.",
    },
    {
        "slug": "profit-optimiser",
        "name": "Profit Optimiser",
        "task": "Suggest actionable ways to increase profit margins and reduce unnecessary costs.",
        "requirements": "You are a financial advisor with over 10 years of experience improving profit margins and eliminating cost inefficiencies for businesses.",
    },
    {
        "slug": "risk-identifier",
        "name": "Risk Identifier",
        "task": "Identify financial, operational, and market risks facing the business.",
        "requirements": "You are a risk management specialist with over 10 years of experience identifying and mitigating financial, operational, and market risks.",
    },
    {
        "slug": "scenario-simulator",
        "name": "Scenario Simulator",
        "task": "Simulate best-case, worst-case, and most likely business scenarios.",
        "requirements": "You are a strategic planner with over 10 years of experience modelling business scenarios and forecasting outcomes under varying conditions.",
    },
    {
        "slug": "resource-optimiser",
        "name": "Resource Optimiser",
        "task": "Recommend how to better allocate and optimise business resources.",
        "requirements": "You are a resource management consultant with over 10 years of experience optimising staff, budget, and time allocation across businesses.",
    },
    {
        "slug": "decision-recommendation",
        "name": "Decision Recommendation",
        "task": "Recommend the best next strategic decision for the business.",
        "requirements": "You are a senior business strategist with over 10 years of experience providing high-impact strategic recommendations tailored to business goals.",
    },
]


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def init_agents_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id          SERIAL PRIMARY KEY,
            slug        VARCHAR(100) UNIQUE NOT NULL,
            name        VARCHAR(200) NOT NULL,
            task        TEXT NOT NULL,
            requirements TEXT NOT NULL,
            type        VARCHAR(20) NOT NULL DEFAULT 'default' CHECK (type IN ('default', 'custom')),
            is_disabled BOOLEAN NOT NULL DEFAULT FALSE,
            max_tokens  INT NOT NULL DEFAULT 4096,
            temperature NUMERIC(4,2) NOT NULL DEFAULT 1.0,
            top_p       NUMERIC(4,2) NOT NULL DEFAULT 0.5,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for agent in DEFAULT_AGENTS:
        cur.execute("""
            INSERT INTO agents (slug, name, task, requirements, type)
            VALUES (%s, %s, %s, %s, 'default')
            ON CONFLICT (slug) DO NOTHING
        """, (agent["slug"], agent["name"], agent["task"], agent["requirements"]))
    conn.commit()
    cur.close()
    conn.close()


def get_all_agents():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, slug, name, task, requirements, type, is_disabled, max_tokens, temperature, top_p, created_at
        FROM agents ORDER BY type, name
    """)
    rows = cur.fetchall()
    result = [_row_to_dict(row, cur.description) for row in rows]
    cur.close()
    conn.close()
    return result


def get_agent(slug: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, slug, name, task, requirements, type, is_disabled, max_tokens, temperature, top_p, created_at
        FROM agents WHERE slug = %s
    """, (slug,))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    cur.close()
    conn.close()
    return result


def update_agent(slug: str, updates: dict):
    allowed = {"task", "requirements", "is_disabled", "max_tokens", "temperature", "top_p"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return get_agent(slug)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [slug]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE agents SET {set_clause} WHERE slug = %s "
        f"RETURNING id, slug, name, task, requirements, type, is_disabled, created_at",
        values,
    )
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result


def create_agent(data: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agents (slug, name, task, requirements, type)
        VALUES (%s, %s, %s, %s, 'custom')
        RETURNING id, slug, name, task, requirements, type, is_disabled, max_tokens, temperature, top_p, created_at
    """, (data["slug"], data["name"], data["task"], data["requirements"]))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description)
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_agent(slug: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM agents WHERE slug = %s AND type = 'custom' RETURNING id", (slug,))
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted