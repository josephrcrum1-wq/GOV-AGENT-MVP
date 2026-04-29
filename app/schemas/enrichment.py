from pydantic import BaseModel
from typing import Optional


class OpportunityEnrichmentCreate(BaseModel):
    profile_id: int
    notice_id: str
    known_requirements: Optional[str] = ""
    compliance_requirements: Optional[str] = ""
    place_of_performance: Optional[str] = ""
    clearance_requirements: Optional[str] = ""
    deliverables: Optional[str] = ""
    period_of_performance: Optional[str] = ""
    incumbent_or_competitors: Optional[str] = ""
    submission_deadline: Optional[str] = ""
    customer_priorities: Optional[str] = ""
    questions_or_unknowns: Optional[str] = ""
    additional_notes: Optional[str] = ""