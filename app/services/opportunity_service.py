from sqlalchemy.orm import Session
from app.db import crud
from app.services.document_service import save_document_links


def save_opportunities(db: Session, opportunities: list[dict]) -> int:
    saved_count = 0

    for opp in opportunities:
        if not opp.get("notice_id"):
            continue

        document_links = opp.pop("document_links", [])

        crud.upsert_opportunity(db, opp)

        if document_links:
            save_document_links(
                db=db,
                notice_id=opp["notice_id"],
                document_links=document_links,
            )

        saved_count += 1

    return saved_count


def get_local_opportunities(db: Session, limit: int = 100) -> list[dict]:
    rows = crud.get_all_opportunities(db, limit=limit)

    return [
        {
            "notice_id": row.notice_id,
            "title": row.title,
            "agency": row.agency,
            "posted_date": row.posted_date,
            "response_deadline": row.response_deadline,
            "naics_code": row.naics_code,
            "set_aside": row.set_aside,
            "description_url": row.description_url,
            "description": row.description,
        }
        for row in rows
    ]


def count_local_opportunities(db: Session) -> int:
    return crud.count_opportunities(db)

def search_local_opportunities_by_keywords(db: Session, keywords: str, limit: int = 100) -> list[dict]:
    rows = crud.search_opportunities_keyword(db, keywords=keywords, limit=limit)

    return [
        {
            "notice_id": row.notice_id,
            "title": row.title,
            "agency": row.agency,
            "posted_date": row.posted_date,
            "response_deadline": row.response_deadline,
            "naics_code": row.naics_code,
            "set_aside": row.set_aside,
            "description_url": row.description_url,
            "description": row.description,
        }
        for row in rows
    ]

def get_opportunities_by_notice_ids(db: Session, notice_ids: list[str]) -> list[dict]:
    rows = crud.get_opportunities_by_notice_ids(db, notice_ids)

    return [
        {
            "notice_id": row.notice_id,
            "title": row.title,
            "agency": row.agency,
            "posted_date": row.posted_date,
            "response_deadline": row.response_deadline,
            "naics_code": row.naics_code,
            "set_aside": row.set_aside,
            "description_url": row.description_url,
            "description": row.description,
        }
        for row in rows
    ]
def get_local_db_diagnostics(db: Session) -> dict:
    return crud.get_opportunity_diagnostics(db)