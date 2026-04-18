# Request/response schemas
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    revenue: float
    cost: float
    demand: int