import json
from openai import OpenAI

from app.core.config import settings
from app.services.document_service import get_combined_document_text

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def review_proposal_draft(
    db,
    profile,
    opportunity: dict,
    proposal_plan: dict,
    proposal_draft: dict,
    enrichment: dict | None = None,
) -> dict:
    enrichment = enrichment or {}
    proposal_plan = proposal_plan or {}
    proposal_draft = proposal_draft or {}

    document_text = get_combined_document_text(
        db=db,
        notice_id=opportunity.get("notice_id", ""),
        max_chars=12000,
    )

    prompt = f"""
You are a senior government contracting capture advisor reviewing a proposal draft.

Your job is to assess compliance risk, clarity, and competitiveness — NOT to make the proposal sound better at the expense of accuracy.

CRITICAL RULES:
- Do NOT invent facts, metrics, certifications, compliance claims, or past performance.
- Do NOT claim compliance unless it is explicitly supported by known requirements.
- Do NOT add percentages, performance metrics, named contracts, customer outcomes, incumbent details, staffing credentials, certifications, or tools unless they are provided in the company profile, human enrichment, extracted documents, proposal plan, or proposal draft.
- If information is missing, explicitly state it is missing.
- Preserve uncertainty where appropriate.
- Prefer defensible language over persuasive language.
- If something is inferred, label it as an assumption.
- If a claim is unsupported, either remove it or replace it with a bracketed placeholder.

COMPLIANCE GUIDANCE:
- If requirements are unclear or incomplete, state:
  "Compliance will be confirmed through a formal compliance matrix upon receipt/review of the full solicitation."
- Identify where the proposal risks failing human review or automated screening because of missing keywords, vague language, lack of requirement traceability, or unsupported claims.
- Where possible, map statements to requirement categories such as technical, management, staffing, past performance, compliance, risk, or schedule.

REVISION RULES:
- Improve clarity, structure, and defensibility.
- Remove vague or generic language.
- Replace unsupported claims with placeholders such as:
  [insert verified metric]
  [confirm requirement]
  [add past performance example]
  [identify named system/tool if applicable]
  [confirm staffing qualification]
- Strengthen alignment to government expectations: clarity, traceability, specificity, and compliance discipline.
- Do NOT make the proposal longer unless necessary.
- Do NOT rewrite everything. Preserve useful content and improve weak sections.
- Revisions must use ONLY the provided evidence.
- The revised proposal should remain proposal-ready but cautious where information is missing.

COMPANY PROFILE:
Company: {getattr(profile, "company_name", "")}
Capabilities: {getattr(profile, "capability_summary", "")}
NAICS: {getattr(profile, "naics_codes", "")}
PSC: {getattr(profile, "psc_codes", "")}
Keywords: {getattr(profile, "keywords", "")}
Set-Aside Status: {getattr(profile, "set_aside_status", "")}
Agencies of Interest: {getattr(profile, "agencies_of_interest", "")}
Past Performance: {getattr(profile, "past_performance_summary", "")}

OPPORTUNITY:
Notice ID: {opportunity.get("notice_id")}
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
NAICS: {opportunity.get("naics_code")}
Set-Aside: {opportunity.get("set_aside")}
Summary: {opportunity.get("description")}

EXTRACTED SOLICITATION / SUPPORTING DOCUMENT TEXT:
{document_text}

HUMAN-PROVIDED OPPORTUNITY CONTEXT:
{json.dumps(enrichment, indent=2)}

PROPOSAL PLAN:
{json.dumps(proposal_plan, indent=2)}

PROPOSAL DRAFT:
{json.dumps(proposal_draft, indent=2)}

Return ONLY valid JSON with this exact structure:

{{
  "overall_assessment": "High-level evaluation focused on proposal readiness, risk, and defensibility.",
  "screening_risks": [
    "Risk that could weaken human or automated review"
  ],
  "compliance_gaps": [
    "Missing or weak compliance item"
  ],
  "section_feedback": {{
    "executive_summary": "Specific feedback.",
    "technical_approach": "Specific feedback.",
    "management_plan": "Specific feedback.",
    "past_performance": "Specific feedback.",
    "staffing_plan": "Specific feedback."
  }},
  "recommended_revisions": [
    "Actionable recommendation"
  ],
  "revised_proposal": {{
    "executive_summary": "Revised executive summary using only provided evidence.",
    "technical_approach": "Revised technical approach using only provided evidence.",
    "management_plan": "Revised management plan using only provided evidence.",
    "past_performance": "Revised past performance using only provided evidence.",
    "staffing_plan": "Revised staffing plan using only provided evidence."
  }},
  "assumptions": [
    "Clearly labeled assumption"
  ],
  "missing_information": [
    "Specific missing information needed to strengthen proposal"
  ],
  "unsupported_claims_removed_or_flagged": [
    "Unsupported claim and how it was handled"
  ],
  "requirement_traceability_notes": [
    {{
      "category": "technical | management | staffing | past performance | compliance | risk | schedule",
      "proposal_area": "Section or claim reviewed",
      "traceability_status": "supported | partially supported | unsupported | missing source requirement",
      "note": "Brief explanation"
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON. Do not include markdown, code fences, "
                        "or commentary. Do not invent unsupported facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        result.setdefault("overall_assessment", "")
        result.setdefault("screening_risks", [])
        result.setdefault("compliance_gaps", [])
        result.setdefault("section_feedback", {})
        result.setdefault("recommended_revisions", [])
        result.setdefault("revised_proposal", {})
        result.setdefault("assumptions", [])
        result.setdefault("missing_information", [])
        result.setdefault("unsupported_claims_removed_or_flagged", [])
        result.setdefault("requirement_traceability_notes", [])

        return result

    except Exception as exc:
        return {
            "overall_assessment": "Proposal review failed.",
            "screening_risks": [str(exc)],
            "compliance_gaps": [],
            "section_feedback": {},
            "recommended_revisions": [],
            "revised_proposal": proposal_draft,
            "assumptions": [],
            "missing_information": ["Valid model response"],
            "unsupported_claims_removed_or_flagged": [],
            "requirement_traceability_notes": [],
        }