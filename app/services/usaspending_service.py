import requests

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


def clean_word(word: str) -> str:
    return "".join(ch for ch in word.lower() if ch.isalnum())


def extract_keywords(text: str) -> list[str]:
    if not text:
        return []

    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "into", "about",
        "services", "service", "support", "contract", "award", "program",
        "system", "systems", "requirement", "requirements", "provide",
        "delivery", "government", "federal",
    }

    words = []
    for word in text.replace("/", " ").replace("-", " ").split():
        cleaned = clean_word(word)
        if len(cleaned) > 3 and cleaned not in stopwords:
            words.append(cleaned)

    deduped = []
    seen = set()
    for word in words:
        if word not in seen:
            deduped.append(word)
            seen.add(word)

    return deduped[:6]


def build_usaspending_payload(opportunity: dict) -> dict:
    title = opportunity.get("title") or ""
    description = opportunity.get("description") or ""
    naics_code = opportunity.get("naics_code") or ""

    search_text = f"{title} {description}"
    keywords = extract_keywords(search_text)

    filters = {
        # Contract award type codes
        "award_type_codes": ["A", "B", "C", "D"],
        "time_period": [
            {
                "start_date": "2021-01-01",
                "end_date": "2026-04-23",
            }
        ],
    }

    if keywords:
        filters["keywords"] = keywords

    if naics_code:
        filters["naics_codes"] = [naics_code]

    payload = {
        "filters": filters,
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "Awarding Sub Agency",
            "Description",
            "Award Type",
        ],
        "page": 1,
        "limit": 10,
        "sort": "Award Amount",
        "order": "desc",
        "subawards": False,
    }

    return payload


def normalize_award(item: dict) -> dict:
    return {
        "award_id": item.get("Award ID", ""),
        "recipient_name": item.get("Recipient Name", ""),
        "award_amount": item.get("Award Amount", ""),
        "start_date": item.get("Start Date", ""),
        "end_date": item.get("End Date", ""),
        "awarding_agency": item.get("Awarding Agency", ""),
        "awarding_sub_agency": item.get("Awarding Sub Agency", ""),
        "description": item.get("Description", ""),
        "award_type": item.get("Award Type", ""),
    }


def search_similar_awards(opportunity: dict) -> list[dict]:
    payload = build_usaspending_payload(opportunity)

    response = requests.post(USASPENDING_URL, json=payload, timeout=30)

    print("USASPENDING STATUS:", response.status_code)
    print("USASPENDING PAYLOAD:", payload)
    print("USASPENDING TEXT:", response.text[:1200])

    response.raise_for_status()

    data = response.json()
    results = data.get("results", []) or []

    return [normalize_award(item) for item in results]

from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def summarize_awards_with_llm(awards: list[dict]) -> str:
    if not awards:
        return ""

    sample = awards[:5]

    formatted = ""
    for a in sample:
        formatted += f"""
Recipient: {a.get('recipient_name')}
Amount: {a.get('award_amount')}
Agency: {a.get('awarding_agency')}
Description: {a.get('description')}
---
"""

    prompt = f"""
You are a government contracting analyst.

Based on the following historical contract awards, provide:

1. What type of work is being performed
2. What kinds of companies typically win these contracts
3. What capabilities are likely required to win

Keep it concise and practical.

Awards:
{formatted}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

def compare_profile_to_awards(profile, awards: list[dict]) -> str:
    from openai import OpenAI
    from app.core.config import settings

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    sample = awards[:5]

    awards_text = ""
    for a in sample:
        awards_text += f"""
Recipient: {a.get('recipient_name')}
Description: {a.get('description')}
"""

    prompt = f"""
You are a government contracting advisor.

Compare the company profile to historical contract winners.

Company:
{profile.capability_summary}

Keywords:
{profile.keywords}

Past Performance:
{profile.past_performance_summary}

Historical Awards:
{awards_text}

Provide:
1. Strengths vs winners
2. Gaps vs winners
3. One practical recommendation

Be concise.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content