from pydantic import BaseModel
from typing import Optional


class CompanyProfileCreate(BaseModel):
    company_name: str
    capability_summary: Optional[str] = None
    naics_codes: Optional[str] = None
    psc_codes: Optional[str] = None
    keywords: Optional[str] = None
    set_aside_status: Optional[str] = None
    contract_min: Optional[int] = None
    contract_max: Optional[int] = None
    agencies_of_interest: Optional[str] = None
    geographic_preferences: Optional[str] = None
    past_performance_summary: Optional[str] = None