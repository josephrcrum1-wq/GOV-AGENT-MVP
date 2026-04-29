from pydantic import BaseModel
from typing import Optional


class AwardSearchRequest(BaseModel):
    profile_id: Optional[int] = None
    notice_id: str
    title: str
    agency: Optional[str] = None
    naics_code: Optional[str] = None
    description: Optional[str] = None