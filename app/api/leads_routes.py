from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from app.db_connection import get_db
from app.models.models import User
from app.models.leads_overview import ChatSession, Agent
from app.models.leads_overview import (
    LeadsOverviewResponse, LeadsOverview,
    ConversionRate,
    ResponseTime, AgentPerformance, SalesPerformance
)

router = APIRouter(prefix="/leads", tags=["Leads Overview"])


def get_now():
    return datetime.now(timezone.utc)


@router.get("/overview", response_model=LeadsOverviewResponse)
def leads_overview(db: Session = Depends(get_db)):
    now = get_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = now - timedelta(days=now.weekday())

    total     = db.query(func.count(User.user_id)).scalar() or 0
    new_today = db.query(func.count(User.user_id)).filter(User.created_at >= today_start).scalar() or 0
    new_week  = db.query(func.count(User.user_id)).filter(User.created_at >= week_start).scalar() or 0
    converted = db.query(func.count(User.user_id)).filter(User.role == "Client").scalar() or 0
    lost      = db.query(func.count(User.user_id)).filter(User.is_inactive == True).scalar() or 0
    rate      = round((converted / total * 100), 2) if total > 0 else 0.0

    # --- Sales Performance per Agent --------------------------------------------------------
    from sqlalchemy import distinct

    agent_rows = (
    db.query(
        ChatSession.agent_id,
            Agent.agent_name.label("agent_name"),             
            func.count(distinct(ChatSession.user_id)).label("leads_handled"),
        )
        .join(Agent, Agent.agent_id == ChatSession.agent_id)  
        .filter(ChatSession.agent_id.isnot(None))
        .group_by(ChatSession.agent_id, Agent.agent_name)   
        .all()
    )

    converted_rows = (
        db.query(
            ChatSession.agent_id,
            func.count(distinct(ChatSession.user_id)).label("converted"),
        )
        .join(User, User.user_id == ChatSession.user_id)
        .filter(
            ChatSession.agent_id.isnot(None),
            User.role == "Client"
        )
        .group_by(ChatSession.agent_id)
        .all()
    )
    converted_map = {str(r.agent_id): r.converted for r in converted_rows}

    agents = []
    for row in agent_rows:
        aid       = str(row.agent_id)
        handled   = row.leads_handled
        conv      = converted_map.get(aid, 0)
        conv_rate = round((conv / handled * 100), 2) if handled > 0 else 0.0
        agents.append(AgentPerformance(
            agent_id=aid,
            agent_name=row.agent_name,    # ← use name here
            leads_handled=handled,
            converted=conv,
            conversion_rate_percent=conv_rate,
        ))

    return LeadsOverviewResponse(
        overview=LeadsOverview(
            total_leads=total,
            new_leads_today=new_today,
            new_leads_this_week=new_week,
            converted_leads=converted,
            lost_leads=lost,
        ),
        conversion=ConversionRate(
            converted_leads=converted,
            total_leads=total,
            conversion_rate_percent=rate,
        ),
        sales_performance=SalesPerformance(agents=agents),
    )