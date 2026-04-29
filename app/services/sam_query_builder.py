def split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_naics_queries(profile) -> list[dict]:
    naics_codes = split_csv(profile.naics_codes)

    queries = []

    for code in naics_codes:
        queries.append({
            "name": f"NAICS {code} - all actionable notices",
            "params": {
                "ncode": code,
                "ptype": ["k", "o", "p", "r"],
            },
        })

    return queries


def build_keyword_queries(profile) -> list[dict]:
    keywords = split_csv(profile.keywords)[:3]

    queries = []

    for keyword in keywords:
        queries.append({
            "name": f"Keyword '{keyword}' - all actionable notices",
            "params": {
                "title": keyword,
                "ptype": ["k", "o", "p", "r"],
            },
        })

    return queries


def build_profile_queries(profile) -> list[dict]:
    # Broader sync: NAICS first, then a few keyword searches
    return build_naics_queries(profile) + build_keyword_queries(profile)