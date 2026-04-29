from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def score_with_llm(profile, opportunity: dict) -> dict:
    prompt = f"""
You are a GOVERNMENT CONTRACTING BUSINESS DEVELOPMENT ANALYST.

Your job is to decide if this opportunity is worth pursuing.

Be STRICT. Most opportunities should NOT score high.

---

SCORING RULES (IMPORTANT):

9-10:
- Direct match to company capabilities
- Strong NAICS alignment
- Clear overlap in services
- Company is very competitive

7-8:
- Strong alignment but not perfect
- Some capability gaps or unclear past performance

5-6:
- Partial match
- Might pursue with teaming or adaptation

3-4:
- Weak relevance
- Not aligned with core capabilities

0-2:
- Not relevant
- Wrong domain or services

---

COMPANY PROFILE:
Capabilities:
{profile.capability_summary}

Keywords:
{profile.keywords}

NAICS:
{profile.naics_codes}

Past Performance:
{profile.past_performance_summary}

---

OPPORTUNITY:
Title:
{opportunity.get("title")}

Agency:
{opportunity.get("agency")}

NAICS:
{opportunity.get("naics_code")}

Description:
{opportunity.get("description")}

---

Return ONLY JSON:

{{
    "score": <0-10 integer>,
    "reason": "short explanation",
    "risk": "biggest concern or gap"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()

        # fallback parsing
        import json
        try:
            return json.loads(text)
        except:
            return {
                "score": 5,
                "reason": "LLM parsing fallback",
                "risk": text
            }

    except Exception as e:
        return {
            "score": 0,
            "reason": "LLM scoring failed",
            "risk": str(e)
        }