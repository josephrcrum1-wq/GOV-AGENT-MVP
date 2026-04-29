from pydantic import BaseModel
from typing import Optional


class ReviewCreate(BaseModel):
    profile_id: int
    notice_id: str
    disposition: str
    reviewer_notes: Optional[str] = None