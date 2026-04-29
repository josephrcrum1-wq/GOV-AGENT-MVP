from collections import Counter
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db import models


# --------------------------------------------------
# Profiles
# --------------------------------------------------
def create_profile(db: Session, profile_data: dict):
    profile = models.CompanyProfile(**profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles(db: Session):
    return db.query(models.CompanyProfile).order_by(models.CompanyProfile.id.desc()).all()


def get_latest_profile(db: Session):
    return db.query(models.CompanyProfile).order_by(models.CompanyProfile.id.desc()).first()


def get_profile_by_id(db: Session, profile_id: int):
    return db.query(models.CompanyProfile).filter(models.CompanyProfile.id == profile_id).first()


def update_profile(db: Session, profile_id: int, profile_data: dict):
    profile = get_profile_by_id(db, profile_id)
    if not profile:
        return None

    for key, value in profile_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


# --------------------------------------------------
# Reviews
# --------------------------------------------------
def create_review(db: Session, review_data: dict):
    existing = (
        db.query(models.Review)
        .filter(
            models.Review.profile_id == review_data["profile_id"],
            models.Review.notice_id == review_data["notice_id"],
        )
        .first()
    )

    if existing:
        existing.disposition = review_data["disposition"]
        existing.reviewer_notes = review_data.get("reviewer_notes")
        db.commit()
        db.refresh(existing)
        return existing

    review = models.Review(**review_data)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_reviews_for_profile(db: Session, profile_id: int):
    return (
        db.query(models.Review)
        .filter(models.Review.profile_id == profile_id)
        .order_by(models.Review.created_at.desc())
        .all()
    )


def get_reviews_by_disposition(db: Session, profile_id: int, disposition: str):
    return (
        db.query(models.Review)
        .filter(
            models.Review.profile_id == profile_id,
            models.Review.disposition == disposition,
        )
        .order_by(models.Review.created_at.desc())
        .all()
    )


# --------------------------------------------------
# Opportunities
# --------------------------------------------------
def upsert_opportunity(db: Session, opportunity_data: dict):
    notice_id = opportunity_data.get("notice_id")

    existing = (
        db.query(models.Opportunity)
        .filter(models.Opportunity.notice_id == notice_id)
        .first()
    )

    if existing:
        for key, value in opportunity_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    opportunity = models.Opportunity(**opportunity_data)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


def get_all_opportunities(db: Session, limit: int = 100):
    return (
        db.query(models.Opportunity)
        .order_by(models.Opportunity.created_at.desc())
        .limit(limit)
        .all()
    )


def count_opportunities(db: Session):
    return db.query(models.Opportunity).count()


def search_opportunities_keyword(db: Session, keywords: str, limit: int = 100):
    rows = db.query(models.Opportunity).all()

    if not keywords:
        return rows[:limit]

    raw_terms = [term.strip().lower() for term in keywords.split(",") if term.strip()]
    today = datetime.today().strftime("%Y-%m-%d")
    results = []

    for row in rows:
        deadline = row.response_deadline or ""

        if deadline and deadline[:10] < today:
            continue

        text = f"""
        {row.title or ""}
        {row.description or ""}
        {row.agency or ""}
        {row.naics_code or ""}
        {row.set_aside or ""}
        """.lower()

        matches = [term for term in raw_terms if term in text]
        score = len(matches)

        results.append((score, row))

    results.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in results[:limit]]


def get_opportunities_by_notice_ids(db: Session, notice_ids: list[str]):
    if not notice_ids:
        return []

    return (
        db.query(models.Opportunity)
        .filter(models.Opportunity.notice_id.in_(notice_ids))
        .all()
    )


def get_opportunity_diagnostics(db: Session):
    rows = db.query(models.Opportunity).all()

    total = len(rows)
    today = datetime.today().strftime("%Y-%m-%d")

    naics_counter = Counter()
    agency_counter = Counter()
    stage_counter = Counter()
    keyword_counter = Counter()

    records_with_description = 0
    records_with_deadline = 0
    expired_count = 0
    active_or_unknown_count = 0

    diagnostic_terms = [
        "osint",
        "open source",
        "intelligence",
        "training",
        "threat",
        "risk",
        "travel",
        "analysis",
        "analytical",
        "research",
        "protective",
        "security",
        "advisory",
        "consulting",
    ]

    for row in rows:
        title = row.title or ""
        description = row.description or ""
        agency = row.agency or "Unknown"
        naics = row.naics_code or "Unknown"
        deadline = row.response_deadline or ""

        text = f"{title} {description} {agency} {naics}".lower()

        naics_counter[naics] += 1
        agency_counter[agency[:120]] += 1

        if description.strip():
            records_with_description += 1

        if deadline.strip():
            records_with_deadline += 1
            if deadline[:10] < today:
                expired_count += 1
            else:
                active_or_unknown_count += 1
        else:
            active_or_unknown_count += 1

        if "sources sought" in text:
            stage_counter["Market Research"] += 1
        elif "presolicitation" in text or "pre-solicitation" in text:
            stage_counter["Monitor"] += 1
        elif "solicitation" in text or "combined synopsis" in text:
            stage_counter["Bid Now"] += 1
        else:
            stage_counter["Unknown"] += 1

        for term in diagnostic_terms:
            if term in text:
                keyword_counter[term] += 1

    return {
        "total_opportunities": total,
        "records_with_description": records_with_description,
        "records_with_deadline": records_with_deadline,
        "expired_count": expired_count,
        "active_or_unknown_count": active_or_unknown_count,
        "top_naics": naics_counter.most_common(10),
        "top_agencies": agency_counter.most_common(10),
        "stage_counts": stage_counter.most_common(),
        "keyword_hits": keyword_counter.most_common(),
    }


# --------------------------------------------------
# Opportunity enrichment
# --------------------------------------------------
def upsert_opportunity_enrichment(db: Session, enrichment_data: dict):
    existing = (
        db.query(models.OpportunityEnrichment)
        .filter(
            models.OpportunityEnrichment.profile_id == enrichment_data["profile_id"],
            models.OpportunityEnrichment.notice_id == enrichment_data["notice_id"],
        )
        .first()
    )

    if existing:
        for key, value in enrichment_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    enrichment = models.OpportunityEnrichment(**enrichment_data)
    db.add(enrichment)
    db.commit()
    db.refresh(enrichment)
    return enrichment


def get_opportunity_enrichment(db: Session, profile_id: int, notice_id: str):
    return (
        db.query(models.OpportunityEnrichment)
        .filter(
            models.OpportunityEnrichment.profile_id == profile_id,
            models.OpportunityEnrichment.notice_id == notice_id,
        )
        .first()
    )