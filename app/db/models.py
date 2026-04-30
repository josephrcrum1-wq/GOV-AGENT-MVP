from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base
from sqlalchemy import Column, Integer, String, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    capability_summary = Column(Text)
    naics_codes = Column(Text)
    psc_codes = Column(Text)
    keywords = Column(Text)
    set_aside_status = Column(String)
    contract_min = Column(Integer)
    contract_max = Column(Integer)
    agencies_of_interest = Column(Text)
    geographic_preferences = Column(Text)
    past_performance_summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    notice_id = Column(String, nullable=False)
    disposition = Column(String, nullable=False)
    reviewer_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(Text)
    agency = Column(Text)
    posted_date = Column(String)
    response_deadline = Column(String)
    naics_code = Column(String)
    set_aside = Column(String)
    description_url = Column(Text)
    description = Column(Text)
    source = Column(String, default="SAM")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OpportunityEnrichment(Base):
    __tablename__ = "opportunity_enrichments"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    notice_id = Column(String, nullable=False)

    known_requirements = Column(Text)
    compliance_requirements = Column(Text)
    place_of_performance = Column(Text)
    clearance_requirements = Column(Text)
    deliverables = Column(Text)
    period_of_performance = Column(Text)
    incumbent_or_competitors = Column(Text)
    submission_deadline = Column(Text)
    customer_priorities = Column(Text)
    questions_or_unknowns = Column(Text)
    additional_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("profile_id", "notice_id", name="uq_profile_notice_enrichment"),
    )

class OpportunityDocument(Base):
    __tablename__ = "opportunity_documents"

    id = Column(Integer, primary_key=True, index=True)
    notice_id = Column(String, index=True, nullable=False)
    document_url = Column(Text, nullable=False)
    document_name = Column(Text)
    document_type = Column(String, default="unknown")
    extracted_text = Column(Text)
    extraction_status = Column(String, default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OpportunityAnalysis(Base):
    __tablename__ = "opportunity_analyses"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, index=True, nullable=False)
    notice_id = Column(String, index=True, nullable=False)
    analysis_type = Column(String, index=True, nullable=False)
    payload = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("profile_id", "notice_id", "analysis_type", name="uq_profile_notice_analysis"),
    )