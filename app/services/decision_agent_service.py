import json
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def run_decision_agent(
    profile,
    opportunity: dict,
    awards: list[dict] | None = None,
    enrichment: dict | None = None,
) -> dict:
    awards = awards or []
    enrichment = enrichment or {}

    awards_text = ""
    for award in awards[:5]:
        awards_text += f"""
Recipient: {award.get('recipient_name')}
Amount: {award.get('award_amount')}
Agency: {award.get('awarding_agency')}
Description: {award.get('description')}
---
"""

    enrichment_text = f"""
Known Requirements: {enrichment.get("known_requirements", "")}
Compliance Requirements: {enrichment.get("compliance_requirements", "")}
Place of Performance: {enrichment.get("place_of_performance", "")}
Clearance Requirements: {enrichment.get("clearance_requirements", "")}
Deliverables: {enrichment.get("deliverables", "")}
Period of Performance: {enrichment.get("period_of_performance", "")}
Incumbent / Competitors: {enrichment.get("incumbent_or_competitors", "")}
Submission Deadline: {enrichment.get("submission_deadline", "")}
Customer Priorities: {enrichment.get("customer_priorities", "")}
Questions / Unknowns: {enrichment.get("questions_or_unknowns", "")}
Additional Notes: {enrichment.get("additional_notes", "")}
"""

    prompt = f"""
You are a government contracting capture analyst.

Evaluate this opportunity for the company profile.

IMPORTANT RULES:
- Do NOT invent contract requirements.
- If details are missing, say they are missing.
- Lower confidence when the opportunity description is thin.
- Use human-provided opportunity context as higher-value evidence than the SAM summary.
- Confidence must be an integer from 0 to 100.

COMPANY PROFILE:
Company: {profile.company_name}
Capabilities: {profile.capability_summary}
NAICS: {profile.naics_codes}
PSC: {profile.psc_codes}
Keywords: {profile.keywords}
Set-Aside Status: {profile.set_aside_status}
Agencies of Interest: {profile.agencies_of_interest}
Past Performance: {profile.past_performance_summary}

OPPORTUNITY:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
NAICS: {opportunity.get("naics_code")}
Set-Aside: {opportunity.get("set_aside")}
Description: {opportunity.get("description")}

HUMAN-PROVIDED OPPORTUNITY CONTEXT:
{enrichment_text}

SIMILAR HISTORICAL AWARDS:
{awards_text}

Return ONLY valid JSON with this exact structure:

{{
  "opportunity_summary": "Summarize the opportunity in plain English.",
  "key_requirements": ["requirement 1", "requirement 2"],
  "decision": "Pursue | Consider Carefully | Do Not Pursue",
  "decision_reasoning": "Explain the decision.",
  "risks": ["risk 1", "risk 2"],
  "suggested_approach": "Recommend positioning, teaming, or next steps.",
  "confidence": 0,
  "missing_information": ["missing item 1", "missing item 2"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content.strip()

    try:
        result = json.loads(text)
        result["confidence"] = int(result.get("confidence", 0))
        result["confidence"] = max(0, min(100, result["confidence"]))
        return result
    except Exception:
        return {
            "opportunity_summary": "Decision agent response could not be parsed.",
            "key_requirements": [],
            "decision": "Consider Carefully",
            "decision_reasoning": "The model response was not valid JSON.",
            "risks": [text[:500]],
            "suggested_approach": "",
            "confidence": 0,
            "missing_information": ["Valid structured model response"],
        }