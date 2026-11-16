from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class RequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=5000)
    customer_segment: str = Field(default="Unspecified", max_length=100)

class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    customer_segment: str
    status: str
    created_at: datetime
    vote_count: int = 0
    theme: Optional[str] = None
    underlying_need: Optional[str] = None
    priority_score: Optional[float] = None

class VoteIn(BaseModel):
    voter_key: str = Field(min_length=2, max_length=120)

class MergeDecision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")

class AnalyseOut(BaseModel):
    request_id: int
    underlying_need: str
    theme: str
    impact: str
    urgency: str
    confidence: float
    rationale: str
    similar_requests: list[dict]

class BriefOut(BaseModel):
    id: int
    title: str
    summary: str
    recommendation: str
    evidence: str
    score: float
