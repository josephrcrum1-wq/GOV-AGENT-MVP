from app.services.llm_service import call_llm
from app.services.document_service import get_combined_document_text


def analyze_opportunity(db, profile, opportunity, enrichment=None):
    opportunity_text = f"""
Title: {opportunity.get('title')}
Agency: {opportunity.get('agency')}
NAICS: {opportunity.get('naics_code')}
Summary: {opportunity.get('description')}
"""

    profile_text = f"""
Capabilities: {profile.capability_summary}
Keywords: {profile.keywords}
Past Performance: {profile.past_performance}
"""

    enrichment_text = ""
    if enrichment:
        enrichment_text = f"""
USER PROVIDED DETAILS:
{enrichment}
"""

    # 🔥 NEW: Pull document text
    document_text = get_combined_document_text(db, opportunity["notice_id"])

    prompt = f"""
You are an expert government contracting analyst.

OPPORTUNITY:
{opportunity_text}

EXTRACTED SOLICITATION DOCUMENT TEXT:
{document_text}

COMPANY PROFILE:
{profile_text}

{enrichment_text}

INSTRUCTIONS:
- Use document evidence when available
- Prioritize document content over summaries
- If requirements are not explicitly stated, list them as missing
- DO NOT assume or invent requirements

OUTPUT FORMAT:
Return JSON with:
- opportunity_summary
- decision (Pursue, Consider Carefully, Do Not Pursue)
- decision_reasoning
- key_requirements (list)
- risks (list)
- suggested_approach
- confidence (0-100)
- missing_information (list)
"""

    return call_llm(prompt)