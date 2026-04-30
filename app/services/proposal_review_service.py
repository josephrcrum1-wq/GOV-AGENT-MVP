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

    document_text = get_combined_document_text(
        db=db,
        notice_id=opportunity.get("notice_id", ""),
        max_chars=12000,
    )

    prompt = f"""
You are a senior federal capture advisor reviewing a proposal draft.

Review the proposal for:
- compliance with stated requirements
- alignment to evaluation priorities
- clarity and persuasiveness
- evidence-backed claims
- missing sections
- vague or unsupported language
- risk of being screened out by human reviewers or automated compliance tools

Important:
- Do NOT invent requirements.
- If the RFP/SOW/PWS does not provide enough information, identify missing information.
- Be direct and practical.
- Recommend improvements that make the proposal more compliant, clearer, and more competitive.

COMPANY PROFILE:
{profile.capability_summary}

PAST PERFORMANCE:
{profile.past_performance_summary}

OPPORTUNITY:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
Description: {opportunity.get("description")}

EXTRACTED DOCUMENT TEXT:
{document_text}

HUMAN ENRICHMENT:
{json.dumps(enrichment, indent=2)}

PROPOSAL PLAN:
{json.dumps(proposal_plan, indent=2)}

PROPOSAL DRAFT:
{json.dumps(proposal_draft, indent=2)}

Return ONLY valid JSON:

{{
  "overall_assessment": "...",
  "screening_risks": ["..."],
  "compliance_gaps": ["..."],
  "section_feedback": {{
    "executive_summary": "...",
    "technical_approach": "...",
    "management_plan": "...",
    "past_performance": "...",
    "staffing_plan": "..."
  }},
  "recommended_revisions": ["..."],
  "revised_proposal": {{
    "executive_summary": "...",
    "technical_approach": "...",
    "management_plan": "...",
    "past_performance": "...",
    "staffing_plan": "..."
  }},
  "assumptions": ["..."],
  "missing_information": ["..."]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    except Exception as exc:
        return {
            "overall_assessment": "Proposal review failed.",
            "screening_risks": [str(exc)],
            "compliance_gaps": [],
            "section_feedback": {},
            "recommended_revisions": [],
            "revised_proposal": {},
            "assumptions": [],
            "missing_information": ["Valid model response"],
        }