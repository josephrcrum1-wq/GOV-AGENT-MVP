import json
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_proposal_plan(
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
Recipient: {award.get("recipient_name")}
Amount: {award.get("award_amount")}
Agency: {award.get("awarding_agency")}
Description: {award.get("description")}
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
You are a federal proposal strategist.

Create a proposal plan for this opportunity.

IMPORTANT RULES:
- Do NOT invent requirements.
- If the opportunity is under-specified, clearly identify missing details.
- Use human-provided opportunity context as primary evidence.
- The output should help a proposal team prepare, not pretend the proposal is complete.

COMPANY:
{profile.capability_summary}

PAST PERFORMANCE:
{profile.past_performance_summary}

KEYWORDS:
{profile.keywords}

OPPORTUNITY:
Title: {opportunity.get("title")}
Agency: {opportunity.get("agency")}
Description: {opportunity.get("description")}

HUMAN-PROVIDED OPPORTUNITY CONTEXT:
{enrichment_text}

SIMILAR HISTORICAL AWARDS:
{awards_text}

Return ONLY valid JSON with this exact structure:

{{
  "summary": "short summary",
  "key_requirements": ["requirement 1", "requirement 2"],
  "win_themes": ["theme 1", "theme 2"],
  "differentiators": ["differentiator 1", "differentiator 2"],
  "risks": ["risk 1", "risk 2"],
  "teaming_strategy": "recommended teaming strategy",
  "proposal_outline": ["Executive Summary", "Technical Approach", "Management Plan", "Past Performance", "Staffing Plan"],
  "missing_information": ["missing item 1", "missing item 2"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON. Do not include markdown, code fences, or commentary.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        return {
            "summary": "Proposal plan could not be parsed.",
            "key_requirements": [],
            "win_themes": [],
            "differentiators": [],
            "risks": [content[:500]],
            "teaming_strategy": "",
            "proposal_outline": [],
            "missing_information": ["Valid structured model response"],
        }