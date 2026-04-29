from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class DecisionAnalysisRequest(BaseModel):
    profile_id: int
    opportunity: Dict[str, Any]
    awards: Optional[List[Dict[str, Any]]] = None