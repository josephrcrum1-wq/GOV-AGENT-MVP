from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.schemas.company import CompanyProfileCreate
from app.schemas.opportunity import OpportunitySearchRequest
from app.schemas.review import ReviewCreate
from app.schemas.award import AwardSearchRequest
from app.schemas.decision import DecisionAnalysisRequest
from app.schemas.enrichment import OpportunityEnrichmentCreate

from app.services import profile_service, review_service, opportunity_service, enrichment_service
from app.services.sam_service import search_sam_opportunities
from app.services.ranking_service import rank_opportunities
from app.services.usaspending_service import (
    search_similar_awards,
    summarize_awards_with_llm,
    compare_profile_to_awards,
)
from app.services.decision_agent_service import run_decision_agent
from app.services.proposal_service import generate_proposal_plan
from app.services import document_service
from app.services.proposal_draft_service import generate_full_proposal
from app.services.proposal_review_service import review_proposal_draft
from fastapi.responses import StreamingResponse
from app.services.docx_export_service import build_revised_proposal_docx
from app.services.requirement_service import (
    extract_requirements_from_documents,
    build_compliance_matrix,
)
from app.services import analysis_service
from app.services.proposal_review_service import review_proposal_draft, review_proposal_after_compliance


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gov Agent MVP")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "API running"}


# --------------------------------------------------
# Profile routes
# --------------------------------------------------
@app.post("/profiles")
def create_profile(profile: CompanyProfileCreate, db: Session = Depends(get_db)):
    return profile_service.create_profile(db, profile.model_dump())


@app.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    return profile_service.list_profiles(db)


@app.get("/profiles/latest")
def get_latest_profile(db: Session = Depends(get_db)):
    profile = profile_service.get_latest_profile(db)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found")
    return profile


@app.get("/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.put("/profiles/{profile_id}")
def update_profile(profile_id: int, profile: CompanyProfileCreate, db: Session = Depends(get_db)):
    updated = profile_service.update_profile(db, profile_id, profile.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated


# --------------------------------------------------
# Opportunity routes
# --------------------------------------------------
@app.post("/opportunities/search")
def search_opportunities(payload: OpportunitySearchRequest, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        opportunities = search_sam_opportunities(profile)
        ranked = rank_opportunities(profile, opportunities)
        return ranked

    except Exception as e:
        error_text = str(e)
        print("SEARCH ERROR:", error_text)

        if "429" in error_text:
            raise HTTPException(
                status_code=429,
                detail="SAM API rate limit reached. Wait until quota resets or use local search.",
            )

        raise HTTPException(status_code=500, detail=error_text)


@app.post("/opportunities/sync/{profile_id}")
def sync_sam_opportunities(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        opportunities = search_sam_opportunities(profile)
        saved_count = opportunity_service.save_opportunities(db, opportunities)

        return {
            "message": "SAM sync complete",
            "fetched": len(opportunities),
            "saved": saved_count,
        }

    except Exception as e:
        error_text = str(e)
        print("SYNC ERROR:", error_text)

        if "429" in error_text:
            raise HTTPException(
                status_code=429,
                detail="SAM API rate limit reached. Try again after quota reset.",
            )

        raise HTTPException(status_code=500, detail=error_text)


@app.post("/opportunities/local-search")
def search_local_opportunities(payload: OpportunitySearchRequest, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    opportunities = opportunity_service.search_local_opportunities_by_keywords(
        db=db,
        keywords=profile.keywords or "",
        limit=100,
    )

    if not opportunities:
        opportunities = opportunity_service.get_local_opportunities(db, limit=100)

    ranked = rank_opportunities(profile, opportunities)
    return ranked


@app.get("/opportunities/diagnostics")
def get_opportunity_diagnostics(db: Session = Depends(get_db)):
    return opportunity_service.get_local_db_diagnostics(db)


@app.post("/opportunities/by-ids")
def get_opportunities_by_ids(payload: dict, db: Session = Depends(get_db)):
    notice_ids = payload.get("notice_ids", [])
    return opportunity_service.get_opportunities_by_notice_ids(db, notice_ids)


@app.post("/opportunities/rerank")
def rerank_opportunities(payload: dict, db: Session = Depends(get_db)):
    profile_id = payload.get("profile_id")
    opportunities = payload.get("opportunities", [])

    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return rank_opportunities(profile, opportunities)


# --------------------------------------------------
# Demo opportunities
# --------------------------------------------------
DEMO_OPPORTUNITIES = [
    {
        "notice_id": "DEMO-001",
        "title": "Protective Intelligence and Threat Analysis Training Support",
        "agency": "Department of Homeland Security",
        "posted_date": "2026-04-15",
        "response_deadline": "2026-05-01",
        "naics_code": "928110",
        "set_aside": "SDVOSB",
        "description_url": "",
        "description": "Provide training and analytical support focused on protective intelligence, threat analysis, travel risk, and operational awareness for government personnel.",
    },
    {
        "notice_id": "DEMO-002",
        "title": "Open-Source Intelligence Analytical Support Services",
        "agency": "Department of State",
        "posted_date": "2026-04-12",
        "response_deadline": "2026-04-30",
        "naics_code": "928110",
        "set_aside": "Small Business",
        "description_url": "",
        "description": "Support open-source intelligence collection, public records research, digital risk analysis, and production of intelligence summaries for federal stakeholders.",
    },
]


@app.get("/opportunities/demo/{profile_id}")
def search_demo_opportunities(profile_id: int, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return rank_opportunities(profile, DEMO_OPPORTUNITIES)


# --------------------------------------------------
# Review routes
# --------------------------------------------------
@app.post("/reviews")
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    try:
        return review_service.create_review(db, payload.model_dump())
    except Exception as e:
        print("REVIEW ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews/{profile_id}")
def get_reviews(profile_id: int, db: Session = Depends(get_db)):
    return review_service.get_reviews_for_profile(db, profile_id)


@app.get("/reviews/{profile_id}/disposition/{disposition}")
def get_reviews_by_disposition(profile_id: int, disposition: str, db: Session = Depends(get_db)):
    return review_service.get_reviews_by_disposition(db, profile_id, disposition)


# --------------------------------------------------
# Enrichment routes
# --------------------------------------------------
@app.post("/enrichment")
def save_enrichment(payload: OpportunityEnrichmentCreate, db: Session = Depends(get_db)):
    return enrichment_service.save_enrichment(db, payload.model_dump())


@app.get("/enrichment/{profile_id}/{notice_id}")
def get_enrichment(profile_id: int, notice_id: str, db: Session = Depends(get_db)):
    enrichment = enrichment_service.get_enrichment(db, profile_id, notice_id)
    if not enrichment:
        return {}
    return enrichment


# --------------------------------------------------
# Award routes
# --------------------------------------------------
@app.post("/awards/similar")
def get_similar_awards(payload: AwardSearchRequest, db: Session = Depends(get_db)):
    try:
        opportunity = {
            "notice_id": payload.notice_id,
            "title": payload.title,
            "agency": payload.agency,
            "naics_code": payload.naics_code,
            "description": payload.description,
        }

        awards = search_similar_awards(opportunity)

        try:
            summary = summarize_awards_with_llm(awards)
        except Exception as summary_error:
            print("LLM SUMMARY ERROR:", summary_error)
            summary = ""

        comparison = ""
        if getattr(payload, "profile_id", None):
            profile = profile_service.get_profile_by_id(db, payload.profile_id)
            if profile:
                try:
                    comparison = compare_profile_to_awards(profile, awards)
                except Exception as comparison_error:
                    print("COMPARISON ERROR:", comparison_error)
                    comparison = ""

        return {
            "awards": awards,
            "summary": summary,
            "comparison": comparison,
        }

    except Exception as e:
        print("USASPENDING ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# Decision agent route
# --------------------------------------------------
@app.post("/decision/analyze")
def analyze_decision(payload: DecisionAnalysisRequest, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    enrichment = enrichment_service.get_enrichment(
        db,
        profile_id=payload.profile_id,
        notice_id=payload.opportunity.get("notice_id", ""),
    ) or {}

    try:
        return run_decision_agent(
            db=db,
            profile=profile,
            opportunity=payload.opportunity,
            awards=payload.awards or [],
            enrichment=enrichment,
        )
    except Exception as e:
        print("DECISION AGENT ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# Proposal route
# --------------------------------------------------
@app.post("/proposal/plan")
def proposal_plan(payload: dict, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload["profile_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    enrichment = enrichment_service.get_enrichment(
        db,
        profile_id=payload["profile_id"],
        notice_id=payload["opportunity"].get("notice_id", ""),
    ) or {}

    return generate_proposal_plan(
        db=db,
        profile=profile,
        opportunity=payload["opportunity"],
        awards=payload.get("awards", []),
        enrichment=enrichment,
    )

@app.post("/documents/process")
def process_documents(limit: int = 10, db: Session = Depends(get_db)):
    return document_service.process_pending_documents(db, limit=limit)


@app.get("/documents/{notice_id}")
def get_documents_for_notice(notice_id: str, db: Session = Depends(get_db)):
    return document_service.get_documents_for_notice(db, notice_id)

@app.post("/documents/process-reviewed/{profile_id}")
def process_reviewed_documents(profile_id: int, limit: int = 10, db: Session = Depends(get_db)):
    return document_service.process_documents_for_reviewed_opportunities(
        db=db,
        profile_id=profile_id,
        limit=limit,
    )


@app.post("/documents/upload")
def upload_document(
    notice_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return document_service.upload_and_extract_document(
        db=db,
        notice_id=notice_id,
        file=file,
    )

@app.post("/proposal/full")
def full_proposal(payload: dict, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload["profile_id"])

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    enrichment = enrichment_service.get_enrichment(
        db,
        profile_id=payload["profile_id"],
        notice_id=payload["opportunity"].get("notice_id", ""),
    ) or {}

    return generate_full_proposal(
        db=db,
        profile=profile,
        opportunity=payload["opportunity"],
        proposal_plan=payload.get("proposal_plan", {}),
        enrichment=enrichment,
    )

@app.post("/proposal/review")
def review_proposal(payload: dict, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload["profile_id"])

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    enrichment = enrichment_service.get_enrichment(
        db,
        profile_id=payload["profile_id"],
        notice_id=payload["opportunity"].get("notice_id", ""),
    ) or {}

    return review_proposal_draft(
        db=db,
        profile=profile,
        opportunity=payload["opportunity"],
        proposal_plan=payload.get("proposal_plan", {}),
        proposal_draft=payload.get("proposal_draft", {}),
        enrichment=enrichment,
    )

@app.post("/proposal/export-docx")
def export_proposal_docx(payload: dict):
    revised_proposal = payload.get("revised_proposal", {})
    review = payload.get("review", {})

    file_stream = build_revised_proposal_docx(
        revised_proposal=revised_proposal,
        review=review,
    )

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": "attachment; filename=revised_proposal_draft.docx"
        },
    )

@app.post("/requirements/extract")
def extract_requirements(payload: dict, db: Session = Depends(get_db)):
    return extract_requirements_from_documents(
        db=db,
        opportunity=payload.get("opportunity", {}),
    )


@app.post("/requirements/compliance-matrix")
def compliance_matrix(payload: dict, db: Session = Depends(get_db)):
    return build_compliance_matrix(
        db=db,
        opportunity=payload.get("opportunity", {}),
        requirements_result=payload.get("requirements_result", {}),
        proposal_draft=payload.get("proposal_draft", {}),
        revised_proposal=payload.get("revised_proposal", {}),
    )

@app.get("/analysis/{profile_id}/{notice_id}")
def load_analysis(profile_id: int, notice_id: str, db: Session = Depends(get_db)):
    return analysis_service.load_all_analysis(
        db=db,
        profile_id=profile_id,
        notice_id=notice_id,
    )


@app.post("/analysis/save")
def save_analysis(payload: dict, db: Session = Depends(get_db)):
    return analysis_service.save_analysis(
        db=db,
        profile_id=payload["profile_id"],
        notice_id=payload["notice_id"],
        analysis_type=payload["analysis_type"],
        payload=payload.get("payload", {}),
    )

@app.post("/proposal/final-review")
def final_proposal_review(payload: dict, db: Session = Depends(get_db)):
    profile = profile_service.get_profile_by_id(db, payload["profile_id"])

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    enrichment = enrichment_service.get_enrichment(
        db,
        profile_id=payload["profile_id"],
        notice_id=payload["opportunity"].get("notice_id", ""),
    ) or {}

    return review_proposal_after_compliance(
        db=db,
        profile=profile,
        opportunity=payload.get("opportunity", {}),
        proposal_draft=payload.get("proposal_draft", {}),
        advisor_review=payload.get("advisor_review", {}),
        compliance_matrix=payload.get("compliance_matrix", {}),
        enrichment=enrichment,
    )