from app.services.llm_ranking_service import score_with_llm


def split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def determine_stage(opportunity: dict) -> str:
    text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()

    if "combined synopsis" in text or "solicitation" in text:
        return "Bid Now"
    elif "sources sought" in text:
        return "Market Research"
    elif "presolicitation" in text or "pre-solicitation" in text:
        return "Monitor"
    else:
        return "Low Priority"


def is_potentially_relevant(profile, opportunity: dict) -> bool:
    text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()

    broad_terms = [
        "training",
        "analysis",
        "analytical",
        "support",
        "intelligence",
        "research",
        "risk",
        "advisory",
        "consulting",
        "security",
        "operations",
        "threat",
        "travel",
        "investigation",
        "investigative",
        "open source",
        "osint",
    ]

    return any(term in text for term in broad_terms)


def score_opportunity_rules(profile, opportunity: dict) -> dict:
    score = 0
    reasons = []
    flags = []

    profile_naics = split_csv(profile.naics_codes)
    profile_keywords = split_csv(profile.keywords)
    profile_agencies = split_csv(profile.agencies_of_interest)
    profile_set_aside = (profile.set_aside_status or "").lower()

    opp_naics = (opportunity.get("naics_code") or "").lower()
    opp_title = (opportunity.get("title") or "").lower()
    opp_desc = (opportunity.get("description") or "").lower()
    opp_agency = (opportunity.get("agency") or "").lower()
    opp_set_aside = (opportunity.get("set_aside") or "").lower()

    combined_text = f"{opp_title} {opp_desc}"

    if opp_naics and opp_naics in profile_naics:
        score += 25
        reasons.append("Exact NAICS match")

    keyword_hits = []
    for kw in profile_keywords:
        if kw in combined_text:
            keyword_hits.append(kw)

    if keyword_hits:
        score += min(len(keyword_hits) * 6, 30)
        reasons.append(f"Keyword overlap: {', '.join(keyword_hits[:5])}")

    concept_groups = {
        "intelligence": ["intelligence", "analysis", "analytical", "osint", "open source"],
        "training": ["training", "instruction", "curriculum", "education", "workshop"],
        "support": ["support", "services", "assistance", "program support", "operational support"],
        "risk": ["risk", "threat", "security", "protective", "travel risk"],
        "research": ["research", "public records", "investigation", "due diligence"],
        "advisory": ["advisory", "consulting", "subject matter expert", "sme"],
    }

    concept_hits = []
    for concept, terms in concept_groups.items():
        if any(term in combined_text for term in terms):
            score += 5
            concept_hits.append(concept)

    if concept_hits:
        reasons.append(f"Concept match: {', '.join(concept_hits)}")

    if opp_agency and profile_agencies:
        for agency in profile_agencies:
            if agency in opp_agency:
                score += 10
                reasons.append("Agency is in preferred list")
                break

    if profile_set_aside and opp_set_aside:
        if profile_set_aside in opp_set_aside:
            score += 10
            reasons.append("Set-aside alignment")
        else:
            flags.append("Set-aside may not align")

    if score == 0:
        flags.append("No strong rule-based alignment found")

    return {
        "rule_score": score,
        "rule_reasons": reasons,
        "rule_flags": flags,
    }


def rank_opportunities(profile, opportunities: list[dict]) -> list[dict]:
    rule_ranked = []

    # First score everything locally before spending OpenAI calls
    for opp in opportunities:
        rule_result = score_opportunity_rules(profile, opp)
        potentially_relevant = is_potentially_relevant(profile, opp)

        if rule_result["rule_score"] > 0 or potentially_relevant:
            rule_ranked.append({
                **opp,
                **rule_result,
            })

    # Fallback: if local rules filtered out everything, include all records
    if not rule_ranked:
        for opp in opportunities:
            rule_result = score_opportunity_rules(profile, opp)
            rule_ranked.append({
                **opp,
                **rule_result,
            })

    # Sort locally before calling OpenAI
    rule_ranked.sort(key=lambda x: x.get("rule_score", 0), reverse=True)

    # Limit LLM scoring to control cost
    candidates_for_llm = rule_ranked[:25]

    final_ranked = []

    for opp in candidates_for_llm:
        try:
            llm_result = score_with_llm(profile, opp)
            llm_score = int(llm_result.get("score", 0))
            reason = llm_result.get("reason", "")
            risk = llm_result.get("risk", "")
        except Exception as e:
            print("LLM ERROR:", e)
            llm_score = 0
            reason = "LLM scoring failed."
            risk = str(e)

        final_ranked.append({
            **opp,
            "score": llm_score,
            "stage": determine_stage(opp),
            "rule_score": opp.get("rule_score", 0),
            "reasons": [
                f"AI assessment: {reason}",
                f"Rule score: {opp.get('rule_score', 0)}",
            ] + opp.get("rule_reasons", []),
            "flags": ([risk] if risk else []) + opp.get("rule_flags", []),
        })

    final_ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

    scored_notice_ids = {opp.get("notice_id") for opp in final_ranked}

    remaining = []
    for opp in rule_ranked:
        if opp.get("notice_id") not in scored_notice_ids:
            remaining.append({
                **opp,
                "score": 0,
                "stage": determine_stage(opp),
                "rule_score": opp.get("rule_score", 0),
                "reasons": [
                    "Not scored by AI yet. Included for human review.",
                    f"Rule score: {opp.get('rule_score', 0)}",
                ] + opp.get("rule_reasons", []),
                "flags": opp.get("rule_flags", []),
            })

    remaining.sort(key=lambda x: x.get("rule_score", 0), reverse=True)

    return final_ranked + remaining