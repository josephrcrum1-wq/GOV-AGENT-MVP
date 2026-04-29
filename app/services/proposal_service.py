from app.services.llm_service import call_llm
from app.services.document_service import get_combined_document_text


def generate_proposal_plan(db, profile, opportunity, awards=None, enrichment=None):
    opportunity_text = f"""
Title: {opportunity.get('title')}
Agency: {opportunity.get('agency')}
Summary: {opportunity.get('description')}
"""

    profile_text = f"""
Capabilities: {profile.capability_summary}
Keywords: {profile.keywords}
Past Performance: {profile.past_performance}
"""

    awards_text = ""
    if awards:
        awards_text = "\n".join([str(a) for a in awards])

    enrichment_text = ""
    if enrichment:
        enrichment_text = f"""
USER PROVIDED DETAILS:
{enrichment}
"""

    # 🔥 NEW: Document grounding
    document_text = get_combined_document_text(db, opportunity["notice_id"])

    prompt = f"""
You are an expert proposal strategist.

OPPORTUNITY:
{opportunity_text}

EXTRACTED SOLICITATION DOCUMENT TEXT:
{document_text}

COMPANY PROFILE:
{profile_text}

SIMILAR AWARDS:
{awards_text}

{enrichment_text}

INSTRUCTIONS:
- Base proposal strategy on actual document requirements
- If requirements are missing, explicitly state them
- DO NOT invent requirements
- Use realistic government proposal language

OUTPUT FORMAT:
Return JSON with:
- summary
- key_requirements (list)
- win_themes (list)
- differentiators (list)
- risks (list)
- teaming_strategy
- proposal_outline (list)
"""

    return call_llm(prompt)