from pydantic import BaseModel
from typing import Optional
import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ---- Session table --------------------------------------------------------
class ChatSession(Base):
    __tablename__ = "session"

    session_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id     = Column(UUID(as_uuid=True), nullable=True)
    user_id      = Column(VARCHAR(20), ForeignKey("users.user_id"), nullable=False)
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    project_id   = Column(String, nullable=False)
    session_name = Column(VARCHAR(255), nullable=False)


# ---- Agents Table ---------------------------------------------------------
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, VARCHAR
import uuid

class Agent(Base):
    __tablename__ = "agents"

    agent_id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name           = Column(VARCHAR(100), nullable=False)
    type                 = Column(VARCHAR(20), nullable=False)
    isdisable            = Column(Boolean, default=False)
    task                 = Column(VARCHAR(255), nullable=False)
    requirements         = Column(VARCHAR(255), nullable=False)
    max_token            = Column(Integer, nullable=False)
    top_p                = Column(Numeric, nullable=False)
    temperature          = Column(Numeric, nullable=False)
    model_id             = Column(UUID(as_uuid=True), nullable=True)
    conversation_starter = Column(Text, nullable=True)


# -- Leads overview BaseModels --------------------------------------------

class LeadsOverview(BaseModel):
    total_leads: int
    new_leads_today: int
    new_leads_this_week: int
    converted_leads: int
    lost_leads: int

class ConversionRate(BaseModel):
    converted_leads: int
    total_leads: int
    conversion_rate_percent: float

class ResponseTime(BaseModel):
    avg_response_time_minutes: Optional[float]   # requires messages/interactions table
    first_response_time_minutes: Optional[float] # requires messages/interactions table

class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str 
    leads_handled: int
    converted: int
    conversion_rate_percent: float
    revenue: Optional[float] = None # requires orders/deals table

class SalesPerformance(BaseModel):
    agents: list[AgentPerformance]

class LeadsOverviewResponse(BaseModel):
    overview: LeadsOverview
    conversion: ConversionRate
    response_time: Optional[ResponseTime] = None        
    sales_performance: Optional[SalesPerformance] = None  