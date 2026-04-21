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
    business_type: str        # must match BUSINESS_TYPES in workspace_prompt.py
    expected_costs: float
    mode_of_business: Optional[str] = None   # None treated as "n/a"
    brief_description: str
