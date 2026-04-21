# Request/response schemas
from pydantic import BaseModel

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