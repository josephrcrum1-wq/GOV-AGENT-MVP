import requests
from app.core.config import settings
from app.services.sam_query_builder import build_profile_queries, split_csv

SAM_URL = "https://api.sam.gov/opportunities/v2/search"


def base_params() -> dict:
    return {
        "api_key": settings.SAM_API_KEY,
        "postedFrom": "01/01/2026",
        "postedTo": "04/24/2026",
        "limit": 25,
    }


def build_summary(item: dict) -> str:
    parts = []

    if item.get("title"):
        parts.append(f"Title: {item.get('title')}")

    if item.get("fullParentPathName"):
        parts.append(f"Agency: {item.get('fullParentPathName')}")

    if item.get("naicsCode"):
        parts.append(f"NAICS: {item.get('naicsCode')}")

    if item.get("setAside") or item.get("setAsideCode"):
        parts.append(f"Set-Aside: {item.get('setAside') or item.get('setAsideCode')}")

    if item.get("type"):
        parts.append(f"Notice Type: {item.get('type')}")

    if item.get("responseDeadLine") or item.get("reponseDeadLine"):
        parts.append(f"Deadline: {item.get('responseDeadLine') or item.get('reponseDeadLine')}")

    return " | ".join(parts)

def extract_document_links(item: dict) -> list[dict]:
    links = []

    possible_fields = [
        item.get("resourceLinks"),
        item.get("links"),
        item.get("attachments"),
        item.get("documents"),
    ]

    for field in possible_fields:
        if isinstance(field, list):
            for entry in field:
                if isinstance(entry, str):
                    links.append({
                        "url": entry,
                        "name": entry.split("/")[-1],
                        "type": "unknown",
                    })
                elif isinstance(entry, dict):
                    url = (
                        entry.get("url")
                        or entry.get("href")
                        or entry.get("link")
                        or entry.get("resourceUrl")
                    )
                    if url:
                        links.append({
                            "url": url,
                            "name": entry.get("name") or entry.get("title") or url.split("/")[-1],
                            "type": entry.get("type") or "unknown",
                        })

    return links
def normalize_opportunity(item: dict) -> dict:
    return {
        "notice_id": str(
            item.get("noticeId")
            or item.get("solicitationNumber")
            or item.get("id")
            or "UNKNOWN"
        ),
        "title": item.get("title") or "Untitled Opportunity",
        "agency": (
            item.get("fullParentPathName")
            or item.get("organizationType")
            or item.get("department")
            or ""
        ),
        "posted_date": item.get("postedDate") or item.get("publishDate") or "",
        "response_deadline": item.get("responseDeadLine") or item.get("reponseDeadLine") or "",
        "naics_code": str(item.get("naicsCode") or ""),
        "set_aside": item.get("setAside") or item.get("setAsideCode") or "",
        "description_url": item.get("description") or "",
        "description": build_summary(item),
        "document_links": extract_document_links(item),
    }


def passes_profile_filter(profile, opportunity: dict) -> bool:
    profile_terms = [term.lower() for term in split_csv(profile.keywords)]

    if not profile_terms:
        return True

    text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()

    return any(term in text for term in profile_terms)


def search_sam_opportunities(profile) -> list[dict]:
    queries = build_profile_queries(profile)

    all_results = {}

    for query in queries:
        params = base_params()
        params.update(query["params"])

        try:
            response = requests.get(SAM_URL, params=params, timeout=30)

            print("SAM QUERY:", query["name"])
            print("SAM STATUS:", response.status_code)
            print("SAM URL:", response.url)
            print("SAM TEXT:", response.text[:500])

            response.raise_for_status()

            data = response.json()
            raw_items = data.get("opportunitiesData", []) or []

            for item in raw_items:
                normalized = normalize_opportunity(item)

                #if not passes_profile_filter(profile, normalized):
                    #continue

                notice_id = normalized.get("notice_id")

                if notice_id and notice_id != "UNKNOWN":
                    all_results[notice_id] = normalized

        except Exception as e:
            print(f"SAM QUERY FAILED: {query['name']} | {e}")
            continue

    return list(all_results.values())