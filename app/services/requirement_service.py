import json
from openai import OpenAI

from app.core.config import settings
from app.services.document_service import get_combined_document_text

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_requirements_from_documents(db, opportunity: dict) -> dict:
    notice_id = opportunity.get("notice_id", "")

    document_text = get_combined_document_text(
        db=db,
        notice_id=notice_id,
        max_chars=20000,
    )

    if not document_text.strip():
        return {
            "notice_id": notice_id,
            "requirements": [],
            "missing_information": ["No extracted document text found for this opportunity."],
        }

    prompt = f"""
You are a federal proposal compliance analyst.

Extract actionable requirements from the opportunity document text.

Rules:
- Extract only requirements that are explicitly supported by the document text.
- Do not invent requirements.
- Classify each requirement.
- Include short evidence excerpts.
- If a requirement is vague, preserve the original wording and mark it as ambiguous.
- Focus on proposal-relevant requirements.

Opportunity:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
NAICS: {opportunity.get("naics_code")}
Summary: {opportunity.get("description")}

Document Text:
{document_text}

Return ONLY valid JSON:

{{
  "notice_id": "{notice_id}",
  "requirements": [
    {{
    "id": "REQ-001",
    "category": "technical | management | staffing | past_performance | compliance | reporting | schedule | submission | other",
    "requirement": "Clear requirement statement.",
    "source_document": "Name of the document if identifiable, otherwise Unknown",
    "source_excerpt": "Short excerpt from source text.",
    "priority": "high | medium | low",
    "ambiguity": "clear | ambiguous"
    }}
  ],
  "missing_information": [
    "Information that could not be extracted but may be needed."
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        result.setdefault("notice_id", notice_id)
        result.setdefault("requirements", [])
        result.setdefault("missing_information", [])

        return result

    except Exception as exc:
        return {
            "notice_id": notice_id,
            "requirements": [],
            "missing_information": [f"Requirement extraction failed: {str(exc)}"],
        }


def build_compliance_matrix(
    db,
    opportunity: dict,
    requirements_result: dict,
    proposal_draft: dict | None = None,
    revised_proposal: dict | None = None,
) -> dict:
    proposal_draft = proposal_draft or {}
    revised_proposal = revised_proposal or {}

    document_text = get_combined_document_text(
        db=db,
        notice_id=opportunity.get("notice_id", ""),
        max_chars=12000,
    )

    requirements = requirements_result.get("requirements", [])

    proposal_to_check = revised_proposal if revised_proposal else proposal_draft

    if not requirements:
        return {
            "overall_status": "No requirements available",
            "matrix": [],
            "summary": "No extracted requirements were available to evaluate.",
            "major_gaps": ["Run requirement extraction first."],
        }

    prompt = f"""
You are a federal proposal compliance reviewer.

Build a compliance matrix comparing extracted requirements against the proposal draft.

Rules:
- Do not invent compliance.
- If the proposal does not clearly address a requirement, mark it as Missing or Partial.
- Use Conservative judgment.
- Cite the proposal section where addressed.
- Identify exact gaps.
- Recommend specific fixes.
- If the proposal contains unsupported claims, flag them.
- Include source_document using the document heading/name if available from the document text. If not identifiable, use "Unknown".
- Preserve source_document and source_excerpt from each extracted requirement in the matrix.

Opportunity:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}

Extracted Requirements:
{json.dumps(requirements, indent=2)}

Proposal Draft To Review:
{json.dumps(proposal_to_check, indent=2)}

Supporting Document Text:
{document_text}

Return ONLY valid JSON:

{{
  "overall_status": "Compliant | Partially Compliant | Not Compliant | Insufficient Information",
  "summary": "Short compliance readiness summary.",
  "matrix": [
    {{
    "requirement_id": "REQ-001",
    "category": "technical",
    "requirement": "Requirement text",
    "source_document": "Source document from extracted requirement",
    "source_excerpt": "Source excerpt from extracted requirement",
    "status": "Addressed | Partial | Missing | Not Applicable | Insufficient Information",
    "proposal_section": "executive_summary | technical_approach | management_plan | past_performance | staffing_plan | none",
    "evidence_from_proposal": "Short excerpt or paraphrase from proposal.",
    "gap": "What is missing or weak.",
    "recommended_fix": "Specific fix."
    }}
  ],
  "major_gaps": ["gap 1", "gap 2"],
  "unsupported_claims": ["claim 1", "claim 2"],
  "recommended_next_steps": ["step 1", "step 2"]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        result.setdefault("overall_status", "Insufficient Information")
        result.setdefault("summary", "")
        result.setdefault("matrix", [])
        result.setdefault("major_gaps", [])
        result.setdefault("unsupported_claims", [])
        result.setdefault("recommended_next_steps", [])

        return result

    except Exception as exc:
        return {
            "overall_status": "Error",
            "summary": "Compliance matrix generation failed.",
            "matrix": [],
            "major_gaps": [str(exc)],
            "unsupported_claims": [],
            "recommended_next_steps": [],
        }