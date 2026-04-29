from pydantic import BaseModel
from typing import Optional, List


class OpportunitySearchRequest(BaseModel):
    profile_id: int


class RankedOpportunity(BaseModel):
    notice_id: str
    title: str
    agency: Optional[str] = None
    posted_date: Optional[str] = None
    response_deadline: Optional[str] = None
    naics_code: Optional[str] = None
    set_aside: Optional[str] = None
    description: Optional[str] = None
    score: int
    reasons: List[str]
    flags: List[str]