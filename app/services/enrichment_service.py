from sqlalchemy.orm import Session
from app.db import crud


def save_enrichment(db: Session, enrichment_data: dict):
    return crud.upsert_opportunity_enrichment(db, enrichment_data)


def get_enrichment(db: Session, profile_id: int, notice_id: str):
    row = crud.get_opportunity_enrichment(db, profile_id, notice_id)

    if not row:
        return None

    return {
        "profile_id": row.profile_id,
        "notice_id": row.notice_id,
        "known_requirements": row.known_requirements or "",
        "compliance_requirements": row.compliance_requirements or "",
        "place_of_performance": row.place_of_performance or "",
        "clearance_requirements": row.clearance_requirements or "",
        "deliverables": row.deliverables or "",
        "period_of_performance": row.period_of_performance or "",
        "incumbent_or_competitors": row.incumbent_or_competitors or "",
        "submission_deadline": row.submission_deadline or "",
        "customer_priorities": row.customer_priorities or "",
        "questions_or_unknowns": row.questions_or_unknowns or "",
        "additional_notes": row.additional_notes or "",
    }