from pydantic import BaseModel
from typing import Optional


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
    business_type: str
    expected_costs: float
    mode_of_business: Optional[str] = None
    brief_description: str


class AgentUpdateRequest(BaseModel):
    task: Optional[str] = None
    requirements: Optional[str] = None
    isdisable: Optional[bool] = None
    max_token: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    model_id: Optional[str] = None
    conversation_starter: Optional[str] = None


class AgentCreateRequest(BaseModel):
    agent_name: str
    task: str
    requirements: str
    max_token: int = 4096
    temperature: float = 1.0
    top_p: float = 0.5
    model_id: Optional[str] = None
    conversation_starter: Optional[str] = None


class AgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    task: str
    requirements: str
    type: str
    isdisable: bool
    max_token: int
    temperature: float
    top_p: float


class ProjectCreateRequest(BaseModel):
    user_id: str
    project_name: str
    project_description: Optional[str] = None
    business_name: str
    business_type: str
    business_context: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    goal: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_context: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    goal: Optional[str] = None


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    token_used: Optional[int] = None
    max_token: Optional[int] = None


class SessionCreateRequest(BaseModel):
    user_id: str
    project_id: str
    agent_id: str
    session_name: str


class ChatRequest(BaseModel):
    message: str


class ReferenceCreateRequest(BaseModel):
    user_id: str
    session_id: str
    content: str


class ReferenceUpdateRequest(BaseModel):
    user_id: str
    content: str
