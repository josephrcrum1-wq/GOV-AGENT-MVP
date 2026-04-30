from app.db import crud


def save_analysis(db, profile_id: int, notice_id: str, analysis_type: str, payload: dict) -> dict:
    row = crud.upsert_opportunity_analysis(
        db=db,
        profile_id=profile_id,
        notice_id=notice_id,
        analysis_type=analysis_type,
        payload=payload,
    )

    return {
        "id": row.id,
        "profile_id": row.profile_id,
        "notice_id": row.notice_id,
        "analysis_type": row.analysis_type,
        "payload": row.payload,
        "updated_at": str(row.updated_at),
    }


def load_all_analysis(db, profile_id: int, notice_id: str) -> dict:
    rows = crud.get_opportunity_analyses(db, profile_id, notice_id)

    return {
        row.analysis_type: {
            "payload": row.payload,
            "updated_at": str(row.updated_at),
        }
        for row in rows
    }