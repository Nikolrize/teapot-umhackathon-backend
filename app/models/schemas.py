from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    revenue: float
    cost: float
    demand: int

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str


class WorkspaceContext(BaseModel):
    name: str
    business_type: str        # must match BUSINESS_TYPES in workspace_prompt.py
    expected_costs: float
    mode_of_business: Optional[str] = None   # None treated as "n/a"
    brief_description: str


class AgentUpdateRequest(BaseModel):
    task: Optional[str] = None
    requirements: Optional[str] = None
    is_disabled: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class AgentCreateRequest(BaseModel):
    slug: str
    name: str
    task: str
    requirements: str
    max_tokens: int = 4096
    temperature: float = 1.0
    top_p: float = 0.5


class AgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    task: str
    requirements: str
    type: str
    is_disabled: bool
    created_at: datetime


class ProjectCreateRequest(BaseModel):
    user_id: int
    project_name: str
    project_description: Optional[str] = None
    business_name: str
    business_type: str
    business_context: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    goal: Optional[str] = None


class SessionCreateRequest(BaseModel):
    user_id: int
    project_id: int
    agent_slug: str


class ChatRequest(BaseModel):
    message: str


class ReferenceCreateRequest(BaseModel):
    user_id: int
    session_id: str
    content: str


class ReferenceUpdateRequest(BaseModel):
    user_id: int
    content: str
