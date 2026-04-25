from app.db_connection import get_db_connection

DEFAULT_AGENTS = [
    {
        "agent_name": "Sales Predictor",
        "task": "Predict future sales trends and revenue opportunities.",
        "requirements": "You are a sales analyst with over 10 years of experience forecasting revenue trends and identifying growth opportunities for businesses.",
    },
    {
        "agent_name": "Pain Point Analyzer",
        "task": "Identify the key pain points and operational challenges facing the business.",
        "requirements": "You are an operations consultant with over 10 years of experience diagnosing business inefficiencies and operational challenges.",
    },
    {
        "agent_name": "Profit Optimiser",
        "task": "Suggest actionable ways to increase profit margins and reduce unnecessary costs.",
        "requirements": "You are a financial advisor with over 10 years of experience improving profit margins and eliminating cost inefficiencies for businesses.",
    },
    {
        "agent_name": "Risk Identifier",
        "task": "Identify financial, operational, and market risks facing the business.",
        "requirements": "You are a risk management specialist with over 10 years of experience identifying and mitigating financial, operational, and market risks.",
    },
    {
        "agent_name": "Scenario Simulator",
        "task": "Simulate best-case, worst-case, and most likely business scenarios.",
        "requirements": "You are a strategic planner with over 10 years of experience modelling business scenarios and forecasting outcomes under varying conditions.",
    },
    {
        "agent_name": "Resource Optimiser",
        "task": "Recommend how to better allocate and optimise business resources.",
        "requirements": "You are a resource management consultant with over 10 years of experience optimising staff, budget, and time allocation across businesses.",
    },
    {
        "agent_name": "Decision Recommendation",
        "task": "Recommend the best next strategic decision for the business.",
        "requirements": "You are a senior business strategist with over 10 years of experience providing high-impact strategic recommendations tailored to business goals.",
    },
]


def _row_to_dict(row, description):
    return {desc[0]: val for desc, val in zip(description, row)}


def init_agents_table():
    conn = get_db_connection()
    cur = conn.cursor()
    for agent in DEFAULT_AGENTS:
        cur.execute("""
            INSERT INTO agents (agent_name, type, task, requirements, max_token, top_p, temperature)
            SELECT %s, 'default', %s, %s, 4096, 0.5, 1.0
            WHERE NOT EXISTS (SELECT 1 FROM agents WHERE agent_name = %s)
        """, (agent["agent_name"], agent["task"], agent["requirements"], agent["agent_name"]))
    conn.commit()
    cur.close()
    conn.close()


def get_all_agents():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT agent_id, agent_name, task, requirements, type, isdisable, max_token, temperature, top_p, model_id
        FROM agents ORDER BY type, agent_name
    """)
    rows = cur.fetchall()
    result = [_row_to_dict(row, cur.description) for row in rows]
    cur.close()
    conn.close()
    return result


def get_agent(agent_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT agent_id, agent_name, task, requirements, type, isdisable, max_token, temperature, top_p, model_id
        FROM agents WHERE agent_id = %s
    """, (agent_id,))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description) if row else None
    cur.close()
    conn.close()
    return result


def update_agent(agent_id: str, updates: dict):
    allowed = {"task", "requirements", "isdisable", "max_token", "temperature", "top_p", "model_id"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return get_agent(agent_id)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [agent_id]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE agents SET {set_clause} WHERE agent_id = %s "
        f"RETURNING agent_id, agent_name, task, requirements, type, isdisable, max_token, temperature, top_p, model_id",
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
        INSERT INTO agents (agent_name, task, requirements, type, max_token, top_p, temperature, model_id)
        VALUES (%s, %s, %s, 'custom', %s, %s, %s, %s)
        RETURNING agent_id, agent_name, task, requirements, type, isdisable, max_token, temperature, top_p, model_id
    """, (
        data["agent_name"], data["task"], data["requirements"],
        data.get("max_token", 4096), data.get("top_p", 0.5), data.get("temperature", 1.0),
        data.get("model_id"),
    ))
    row = cur.fetchone()
    result = _row_to_dict(row, cur.description)
    conn.commit()
    cur.close()
    conn.close()
    return result


def delete_agent(agent_id: str) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM agents WHERE agent_id = %s AND type = 'custom' RETURNING agent_id",
        (agent_id,),
    )
    deleted = cur.fetchone() is not None
    conn.commit()
    cur.close()
    conn.close()
    return deleted
