import json
from openai import OpenAI
from app.core.config import settings
from app.services.document_service import get_combined_document_text

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_full_proposal(
    db,
    profile,
    opportunity: dict,
    proposal_plan: dict,
    enrichment: dict | None = None,
):
    enrichment = enrichment or {}

    document_text = get_combined_document_text(
        db=db,
        notice_id=opportunity.get("notice_id", ""),
        max_chars=15000,
    )

    prompt = f"""
You are an expert federal proposal writer.

Write a structured proposal draft based on the inputs below.

IMPORTANT RULES:
- Do NOT invent requirements
- Use document evidence when available
- If information is missing, explicitly note it
- Use formal government proposal tone
- Keep it realistic and professional

COMPANY:
{profile.capability_summary}

PAST PERFORMANCE:
{profile.past_performance_summary}

OPPORTUNITY:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
Summary: {opportunity.get("description")}

EXTRACTED DOCUMENT TEXT:
{document_text}

PROPOSAL PLAN:
{json.dumps(proposal_plan, indent=2)}

USER CONTEXT:
{json.dumps(enrichment, indent=2)}

Generate the following sections:

1. Executive Summary
2. Technical Approach
3. Management Plan
4. Past Performance
5. Staffing Plan

Return JSON:

{{
  "executive_summary": "...",
  "technical_approach": "...",
  "management_plan": "...",
  "past_performance": "...",
  "staffing_plan": "...",
  "assumptions": [],
  "missing_information": []
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "executive_summary": "Failed to generate proposal.",
            "technical_approach": "",
            "management_plan": "",
            "past_performance": "",
            "staffing_plan": "",
            "assumptions": [],
            "missing_information": [str(e)],
        }