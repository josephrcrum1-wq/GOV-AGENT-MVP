import streamlit as st
import requests

import os

API = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Gov Agent MVP", layout="wide")
st.title("Gov Agent MVP - Phase 1")

# --------------------------------------------------
# Session state defaults
# --------------------------------------------------
defaults = {
    "profile_id": None,
    "company_name": "",
    "capability_summary": "",
    "naics_codes": "",
    "psc_codes": "",
    "keywords": "",
    "set_aside_status": "",
    "contract_min": "",
    "contract_max": "",
    "agencies_of_interest": "",
    "geographic_preferences": "",
    "past_performance_summary": "",
    "opportunities": [],
    "reviews": [],
    "reviewed_opps": [],
    "profiles": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def build_profile_payload(
    company_name,
    capability_summary,
    naics_codes,
    psc_codes,
    keywords,
    set_aside_status,
    contract_min,
    contract_max,
    agencies_of_interest,
    geographic_preferences,
    past_performance_summary,
):
    return {
        "company_name": company_name,
        "capability_summary": capability_summary,
        "naics_codes": naics_codes,
        "psc_codes": psc_codes,
        "keywords": keywords,
        "set_aside_status": set_aside_status,
        "contract_min": int(contract_min) if str(contract_min).strip() else None,
        "contract_max": int(contract_max) if str(contract_max).strip() else None,
        "agencies_of_interest": agencies_of_interest,
        "geographic_preferences": geographic_preferences,
        "past_performance_summary": past_performance_summary,
    }


def load_profile_into_session(profile):
    st.session_state["profile_id"] = profile.get("id")
    st.session_state["company_name"] = profile.get("company_name") or ""
    st.session_state["capability_summary"] = profile.get("capability_summary") or ""
    st.session_state["naics_codes"] = profile.get("naics_codes") or ""
    st.session_state["psc_codes"] = profile.get("psc_codes") or ""
    st.session_state["keywords"] = profile.get("keywords") or ""
    st.session_state["set_aside_status"] = profile.get("set_aside_status") or ""
    st.session_state["contract_min"] = "" if profile.get("contract_min") is None else str(profile.get("contract_min"))
    st.session_state["contract_max"] = "" if profile.get("contract_max") is None else str(profile.get("contract_max"))
    st.session_state["agencies_of_interest"] = profile.get("agencies_of_interest") or ""
    st.session_state["geographic_preferences"] = profile.get("geographic_preferences") or ""
    st.session_state["past_performance_summary"] = profile.get("past_performance_summary") or ""


def fetch_profiles():
    try:
        res = requests.get(f"{API}/profiles", timeout=30)
        if res.ok:
            st.session_state["profiles"] = res.json()
        else:
            st.error(res.text)
    except Exception as exc:
        st.error(f"Failed to load profiles: {exc}")


def fetch_saved_reviews():
    profile_id = st.session_state.get("profile_id")
    if not profile_id:
        st.session_state["reviews"] = []
        return

    try:
        res = requests.get(f"{API}/reviews/{profile_id}", timeout=30)
        if res.ok:
            st.session_state["reviews"] = res.json()
        else:
            st.session_state["reviews"] = []
    except Exception:
        st.session_state["reviews"] = []


def get_review_map():
    review_map = {}
    for review in st.session_state.get("reviews", []):
        review_map[review["notice_id"]] = review
    return review_map


def format_money(amount):
    try:
        return f"${float(amount):,.0f}"
    except Exception:
        return str(amount)


def load_enrichment(profile_id, notice_id):
    if not profile_id or not notice_id:
        return {}

    try:
        res = requests.get(f"{API}/enrichment/{profile_id}/{notice_id}", timeout=30)
        if res.ok:
            return res.json() or {}
        st.error(res.text)
        return {}
    except Exception as exc:
        st.error(f"Failed to load enrichment: {exc}")
        return {}


def save_enrichment(payload):
    try:
        res = requests.post(f"{API}/enrichment", json=payload, timeout=30)
        if res.ok:
            st.success("Opportunity enrichment saved.")
            return res.json()
        st.error(res.text)
        return None
    except Exception as exc:
        st.error(f"Failed to save enrichment: {exc}")
        return None


def render_enrichment_form(notice_id):
    profile_id = st.session_state.get("profile_id")
    enrichment_state_key = f"enrichment_{profile_id}_{notice_id}"

    if enrichment_state_key not in st.session_state:
        st.session_state[enrichment_state_key] = load_enrichment(profile_id, notice_id)

    enrichment = st.session_state.get(enrichment_state_key, {}) or {}

    st.markdown("---")
    st.subheader("Human Opportunity Enrichment")
    st.caption(
        "Add known contract details here before running AI analysis or proposal support. "
        "This reduces speculation and improves decision quality."
    )

    with st.form(f"enrichment_form_{notice_id}"):
        known_requirements = st.text_area(
            "Known Requirements",
            value=enrichment.get("known_requirements", ""),
            key=f"known_requirements_{notice_id}",
        )
        compliance_requirements = st.text_area(
            "Compliance Requirements",
            value=enrichment.get("compliance_requirements", ""),
            key=f"compliance_requirements_{notice_id}",
        )
        place_of_performance = st.text_input(
            "Place of Performance",
            value=enrichment.get("place_of_performance", ""),
            key=f"place_of_performance_{notice_id}",
        )
        clearance_requirements = st.text_input(
            "Clearance Requirements",
            value=enrichment.get("clearance_requirements", ""),
            key=f"clearance_requirements_{notice_id}",
        )
        deliverables = st.text_area(
            "Deliverables",
            value=enrichment.get("deliverables", ""),
            key=f"deliverables_{notice_id}",
        )
        period_of_performance = st.text_input(
            "Period of Performance",
            value=enrichment.get("period_of_performance", ""),
            key=f"period_of_performance_{notice_id}",
        )
        incumbent_or_competitors = st.text_area(
            "Incumbent / Known Competitors",
            value=enrichment.get("incumbent_or_competitors", ""),
            key=f"incumbent_or_competitors_{notice_id}",
        )
        submission_deadline = st.text_input(
            "Submission Deadline",
            value=enrichment.get("submission_deadline", ""),
            key=f"submission_deadline_{notice_id}",
        )
        customer_priorities = st.text_area(
            "Customer Priorities",
            value=enrichment.get("customer_priorities", ""),
            key=f"customer_priorities_{notice_id}",
        )
        questions_or_unknowns = st.text_area(
            "Questions / Unknowns",
            value=enrichment.get("questions_or_unknowns", ""),
            key=f"questions_or_unknowns_{notice_id}",
        )
        additional_notes = st.text_area(
            "Additional Notes",
            value=enrichment.get("additional_notes", ""),
            key=f"additional_notes_{notice_id}",
        )

        submitted = st.form_submit_button("Save Opportunity Context")

    if submitted:
        payload = {
            "profile_id": profile_id,
            "notice_id": notice_id,
            "known_requirements": known_requirements,
            "compliance_requirements": compliance_requirements,
            "place_of_performance": place_of_performance,
            "clearance_requirements": clearance_requirements,
            "deliverables": deliverables,
            "period_of_performance": period_of_performance,
            "incumbent_or_competitors": incumbent_or_competitors,
            "submission_deadline": submission_deadline,
            "customer_priorities": customer_priorities,
            "questions_or_unknowns": questions_or_unknowns,
            "additional_notes": additional_notes,
        }

        saved = save_enrichment(payload)
        if saved:
            st.session_state[enrichment_state_key] = payload

    return st.session_state.get(enrichment_state_key, {}) or {}


# --------------------------------------------------
# Company profile section
# --------------------------------------------------
st.header("Company Profile")

with st.form("profile_form"):
    company_name = st.text_input("Company Name", value=st.session_state["company_name"])
    capability_summary = st.text_area("Capability Summary", value=st.session_state["capability_summary"])
    naics_codes = st.text_input("NAICS Codes (comma separated)", value=st.session_state["naics_codes"])
    psc_codes = st.text_input("PSC Codes (comma separated)", value=st.session_state["psc_codes"])
    keywords = st.text_input("Keywords (comma separated)", value=st.session_state["keywords"])
    set_aside_status = st.text_input("Set-Aside Status", value=st.session_state["set_aside_status"])
    contract_min = st.text_input("Minimum Contract Value", value=st.session_state["contract_min"])
    contract_max = st.text_input("Maximum Contract Value", value=st.session_state["contract_max"])
    agencies_of_interest = st.text_input(
        "Agencies of Interest (comma separated)",
        value=st.session_state["agencies_of_interest"],
    )
    geographic_preferences = st.text_input(
        "Geographic Preferences",
        value=st.session_state["geographic_preferences"],
    )
    past_performance_summary = st.text_area(
        "Past Performance Summary",
        value=st.session_state["past_performance_summary"],
    )

    col_save, col_update = st.columns(2)

    with col_save:
        save_new = st.form_submit_button("Save New Profile")

    with col_update:
        update_existing = st.form_submit_button("Update Current Profile")


profile_payload = build_profile_payload(
    company_name,
    capability_summary,
    naics_codes,
    psc_codes,
    keywords,
    set_aside_status,
    contract_min,
    contract_max,
    agencies_of_interest,
    geographic_preferences,
    past_performance_summary,
)

if save_new:
    try:
        res = requests.post(f"{API}/profiles", json=profile_payload, timeout=30)
        if res.ok:
            profile = res.json()
            load_profile_into_session(profile)
            fetch_profiles()
            st.success("New profile saved.")
        else:
            st.error(res.text)
    except Exception as exc:
        st.error(f"Failed to save profile: {exc}")

if update_existing:
    profile_id = st.session_state.get("profile_id")
    if not profile_id:
        st.error("Load a profile first before updating.")
    else:
        try:
            res = requests.put(f"{API}/profiles/{profile_id}", json=profile_payload, timeout=30)
            if res.ok:
                profile = res.json()
                load_profile_into_session(profile)
                fetch_profiles()
                st.success("Profile updated.")
            else:
                st.error(res.text)
        except Exception as exc:
            st.error(f"Failed to update profile: {exc}")


# --------------------------------------------------
# Load profile / reviews section
# --------------------------------------------------
st.header("Load Profile")

col_refresh_profiles, col_select_profile, col_load_latest, col_load_reviews = st.columns(4)

with col_refresh_profiles:
    if st.button("Refresh Profile List"):
        fetch_profiles()

if not st.session_state.get("profiles"):
    fetch_profiles()

profiles = st.session_state.get("profiles", [])

profile_options = {
    f"{p.get('id')} | {p.get('company_name', 'Unnamed Profile')}": p.get("id")
    for p in profiles
}

with col_select_profile:
    if profile_options:
        selected_label = st.selectbox("Select Existing Profile", list(profile_options.keys()))
        selected_profile_id = profile_options[selected_label]

        if st.button("Load Selected Profile"):
            try:
                res = requests.get(f"{API}/profiles/{selected_profile_id}", timeout=30)
                if res.ok:
                    profile = res.json()
                    load_profile_into_session(profile)
                    fetch_saved_reviews()
                    st.success("Selected profile loaded.")
                    st.rerun()
                else:
                    st.error(res.text)
            except Exception as exc:
                st.error(f"Failed to load selected profile: {exc}")
    else:
        st.caption("No saved profiles found.")

with col_load_latest:
    if st.button("Load Latest"):
        try:
            res = requests.get(f"{API}/profiles/latest", timeout=30)
            if res.ok and res.json():
                profile = res.json()
                load_profile_into_session(profile)
                fetch_saved_reviews()
                st.success("Latest profile loaded.")
                st.rerun()
            else:
                st.warning("No profile found.")
        except Exception as exc:
            st.error(f"Failed to load latest profile: {exc}")

with col_load_reviews:
    if st.button("Load Saved Reviews"):
        if not st.session_state.get("profile_id"):
            st.error("Load or save a profile first.")
        else:
            fetch_saved_reviews()

if st.session_state.get("profile_id"):
    st.caption(f"Current Profile ID: {st.session_state['profile_id']}")


# --------------------------------------------------
# Local DB diagnostics section
# --------------------------------------------------
st.header("Local Opportunity Database Diagnostics")

if st.button("Run Local DB Diagnostics"):
    try:
        res = requests.get(f"{API}/opportunities/diagnostics", timeout=30)

        if res.ok:
            diagnostics = res.json()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Stored", diagnostics.get("total_opportunities", 0))

            with col2:
                st.metric("With Description", diagnostics.get("records_with_description", 0))

            with col3:
                st.metric("Expired", diagnostics.get("expired_count", 0))

            with col4:
                st.metric("Active / Unknown", diagnostics.get("active_or_unknown_count", 0))

            st.subheader("Top NAICS Codes")
            for code, count in diagnostics.get("top_naics", []):
                st.write(f"**{code}:** {count}")

            st.subheader("Stage Counts")
            for stage, count in diagnostics.get("stage_counts", []):
                st.write(f"**{stage}:** {count}")

            st.subheader("Keyword Hit Counts")
            for term, count in diagnostics.get("keyword_hits", []):
                st.write(f"**{term}:** {count}")

            st.subheader("Top Agencies")
            for agency, count in diagnostics.get("top_agencies", []):
                st.write(f"**{agency}:** {count}")

        else:
            st.error(res.text)

    except Exception as exc:
        st.error(f"Failed to run diagnostics: {exc}")


# --------------------------------------------------
# Opportunity search section
# --------------------------------------------------
st.header("Search Opportunities")

col_sync, col_local, col_live, col_demo = st.columns(4)

with col_sync:
    if st.button("Sync SAM to Local DB"):
        profile_id = st.session_state.get("profile_id")

        if not profile_id:
            st.error("Load or save a profile first.")
        else:
            try:
                res = requests.post(
                    f"{API}/opportunities/sync/{profile_id}",
                    timeout=120,
                )

                if res.ok:
                    data = res.json()
                    st.success(f"Sync complete. Fetched: {data.get('fetched')} | Saved: {data.get('saved')}")
                elif res.status_code == 429:
                    st.warning("SAM API rate limit reached. Try again after quota reset.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to sync SAM: {exc}")


with col_local:
    if st.button("Search Local Opportunities"):
        profile_id = st.session_state.get("profile_id")

        if not profile_id:
            st.error("Load or save a profile first.")
        else:
            try:
                res = requests.post(
                    f"{API}/opportunities/local-search",
                    json={"profile_id": profile_id},
                    timeout=120,
                )

                if res.ok:
                    st.session_state["opportunities"] = res.json()
                    fetch_saved_reviews()
                    st.success("Loaded ranked local opportunities.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to search local opportunities: {exc}")


with col_live:
    if st.button("Find Matching Opportunities (Live SAM)"):
        profile_id = st.session_state.get("profile_id")

        if not profile_id:
            st.error("Load or save a profile first.")
        else:
            try:
                res = requests.post(
                    f"{API}/opportunities/search",
                    json={"profile_id": profile_id},
                    timeout=120,
                )

                if res.ok:
                    st.session_state["opportunities"] = res.json()
                    fetch_saved_reviews()
                    st.success("Loaded live opportunities.")
                elif res.status_code == 429:
                    st.warning("SAM API rate limit reached. Use local search or try again after quota reset.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to search live opportunities: {exc}")


with col_demo:
    if st.button("Load Demo Results"):
        profile_id = st.session_state.get("profile_id")

        if not profile_id:
            st.error("Load or save a profile first.")
        else:
            try:
                res = requests.get(f"{API}/opportunities/demo/{profile_id}", timeout=60)

                if res.ok:
                    st.session_state["opportunities"] = res.json()
                    fetch_saved_reviews()
                    st.success("Loaded demo-ranked opportunities.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to load demo results: {exc}")


results = st.session_state.get("opportunities", [])
review_map = get_review_map()

st.caption(f"Loaded opportunities in session: {len(results)}")


# --------------------------------------------------
# Shared renderer for full opportunity tools
# --------------------------------------------------
def render_opportunity_tools(opp, prefix="main"):
    notice_id = opp.get("notice_id", "UNKNOWN")
    stage = opp.get("stage", "Unknown")
    existing_review = get_review_map().get(notice_id)

    st.write(f"**Notice ID:** {notice_id}")
    st.write(f"**Agency:** {opp.get('agency', '')}")
    st.write(f"**Posted Date:** {opp.get('posted_date', '')}")
    st.write(f"**Response Deadline:** {opp.get('response_deadline', '')}")
    st.write(f"**NAICS Code:** {opp.get('naics_code', '')}")
    st.write(f"**Stage:** {stage}")
    st.write(f"**Set-Aside:** {opp.get('set_aside', '')}")

    st.write("**Summary:**")
    st.write(opp.get("description") or "No summary available.")

    if opp.get("description_url"):
        st.write(f"**Description URL:** {opp.get('description_url')}")

    if existing_review:
        st.info(f"Saved Review: {existing_review['disposition']}")

    if opp.get("reasons"):
        st.write("**Reasons:**")
        for reason in opp["reasons"]:
            st.write(f"- {reason}")

    if opp.get("flags"):
        st.write("**Flags:**")
        for flag in opp["flags"]:
            st.write(f"- {flag}")

    # --------------------------------------------------
    # Human enrichment
    # --------------------------------------------------
    render_enrichment_form(notice_id)

    # --------------------------------------------------
    # Review buttons
    # --------------------------------------------------
    st.subheader("Review Decision")

    col_good, col_maybe, col_bad = st.columns(3)

    with col_good:
        if st.button("Good Fit", key=f"{prefix}_good_{notice_id}"):
            res = requests.post(
                f"{API}/reviews",
                json={
                    "profile_id": st.session_state["profile_id"],
                    "notice_id": notice_id,
                    "disposition": "Good Fit",
                    "reviewer_notes": "",
                },
                timeout=30,
            )

            if res.ok:
                st.success("Saved Good Fit")
                fetch_saved_reviews()
                st.rerun()
            else:
                st.error(res.text)

    with col_maybe:
        if st.button("Maybe", key=f"{prefix}_maybe_{notice_id}"):
            res = requests.post(
                f"{API}/reviews",
                json={
                    "profile_id": st.session_state["profile_id"],
                    "notice_id": notice_id,
                    "disposition": "Maybe",
                    "reviewer_notes": "",
                },
                timeout=30,
            )

            if res.ok:
                st.success("Saved Maybe")
                fetch_saved_reviews()
                st.rerun()
            else:
                st.error(res.text)

    with col_bad:
        if st.button("Bad Fit", key=f"{prefix}_bad_{notice_id}"):
            res = requests.post(
                f"{API}/reviews",
                json={
                    "profile_id": st.session_state["profile_id"],
                    "notice_id": notice_id,
                    "disposition": "Bad Fit",
                    "reviewer_notes": "",
                },
                timeout=30,
            )

            if res.ok:
                st.success("Saved Bad Fit")
                fetch_saved_reviews()
                st.rerun()
            else:
                st.error(res.text)

    # --------------------------------------------------
    # Historical award analysis
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("Historical Award Analysis")

    awards_state_key = f"{prefix}_similar_awards_{notice_id}"
    awards_summary_key = f"{prefix}_similar_awards_summary_{notice_id}"
    awards_comparison_key = f"{prefix}_similar_awards_comparison_{notice_id}"
    awards_button_key = f"{prefix}_find_awards_button_{notice_id}"

    if st.button("Find Similar Awards", key=awards_button_key):
        try:
            res = requests.post(
                f"{API}/awards/similar",
                json={
                    "profile_id": st.session_state.get("profile_id"),
                    "notice_id": notice_id,
                    "title": opp.get("title", ""),
                    "agency": opp.get("agency", ""),
                    "naics_code": opp.get("naics_code", ""),
                    "description": opp.get("description", ""),
                },
                timeout=120,
            )

            if res.ok:
                data = res.json()

                if isinstance(data, list):
                    st.session_state[awards_state_key] = data
                    st.session_state[awards_summary_key] = ""
                    st.session_state[awards_comparison_key] = ""
                elif isinstance(data, dict):
                    st.session_state[awards_state_key] = data.get("awards", [])
                    st.session_state[awards_summary_key] = data.get("summary", "")
                    st.session_state[awards_comparison_key] = data.get("comparison", "")
                else:
                    st.session_state[awards_state_key] = []
                    st.session_state[awards_summary_key] = ""
                    st.session_state[awards_comparison_key] = ""

                st.success("Similar awards loaded.")
            else:
                st.error(res.text)

        except Exception as exc:
            st.error(f"Failed to search similar awards: {exc}")

    award_summary = st.session_state.get(awards_summary_key, "")
    award_comparison = st.session_state.get(awards_comparison_key, "")
    similar_awards = st.session_state.get(awards_state_key, [])

    if award_summary:
        st.write("### Market Insight")
        st.write(award_summary)

    if award_comparison:
        st.write("### Win Feasibility")
        st.write(award_comparison)

    if isinstance(similar_awards, list) and similar_awards:
        st.write("### Similar Historical Awards")

        for award in similar_awards[:5]:
            st.markdown("----")
            st.write(f"**Recipient:** {award.get('recipient_name', '')}")
            st.write(f"**Award ID:** {award.get('award_id', '')}")
            st.write(f"**Amount:** {format_money(award.get('award_amount', ''))}")
            st.write(f"**Agency:** {award.get('awarding_agency', '')}")
            st.write(f"**Sub-Agency:** {award.get('awarding_sub_agency', '')}")
            st.write(f"**Start Date:** {award.get('start_date', '')}")
            st.write(f"**End Date:** {award.get('end_date', '')}")
            st.write(f"**Award Type:** {award.get('award_type', '')}")

            if award.get("description"):
                st.write(f"**Description:** {award.get('description', '')}")

    # --------------------------------------------------
    # Full AI decision analysis
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("Full AI Decision Analysis")

    decision_state_key = f"{prefix}_decision_analysis_{notice_id}"

    if st.button("Run Full AI Analysis", key=f"{prefix}_decision_button_{notice_id}"):
        try:
            awards_for_context = st.session_state.get(awards_state_key, [])

            res = requests.post(
                f"{API}/decision/analyze",
                json={
                    "profile_id": st.session_state.get("profile_id"),
                    "opportunity": opp,
                    "awards": awards_for_context,
                },
                timeout=120,
            )

            if res.ok:
                st.session_state[decision_state_key] = res.json()
                st.success("Decision analysis complete.")
            else:
                st.error(res.text)

        except Exception as exc:
            st.error(f"Failed to run decision analysis: {exc}")

    decision = st.session_state.get(decision_state_key)

    if decision:
        st.write("### Opportunity Summary")
        st.write(decision.get("opportunity_summary", ""))

        st.write("### Recommendation")
        st.write(f"**{decision.get('decision', '')}**")
        st.write(decision.get("decision_reasoning", ""))

        st.write("### Key Requirements")
        for item in decision.get("key_requirements", []):
            st.write(f"- {item}")

        st.write("### Risks")
        for item in decision.get("risks", []):
            st.write(f"- {item}")

        st.write("### Suggested Approach")
        st.write(decision.get("suggested_approach", ""))

        st.write("### Confidence & Gaps")
        st.write(f"**Confidence:** {decision.get('confidence', 0)}%")
        for item in decision.get("missing_information", []):
            st.write(f"- {item}")

    if decision.get("evidence"):
        st.write("### Evidence")
        for item in decision.get("evidence", []):
            source = item.get("source", "Unknown")
            claim = item.get("claim", "")
            excerpt = item.get("excerpt", "")
            st.write(f"**Source:** {source}")
            st.write(f"- **Supports:** {claim}")
            if excerpt:
                st.write(f"- **Evidence:** {excerpt}")

    if decision.get("assumptions"):
        st.write("### Assumptions")
        for item in decision.get("assumptions", []):
            st.write(f"- {item}")

    # --------------------------------------------------
    # Proposal support
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("Proposal Support")
    st.caption("AI-generated proposal strategy based on your profile, the opportunity, similar historical awards, and human-provided opportunity context.")

    proposal_state_key = f"{prefix}_proposal_plan_{notice_id}"
    proposal_button_key = f"{prefix}_proposal_button_{notice_id}"

    if st.button("Generate Proposal Plan", key=proposal_button_key):
        try:
            awards_for_context = st.session_state.get(awards_state_key, [])

            res = requests.post(
                f"{API}/proposal/plan",
                json={
                    "profile_id": st.session_state.get("profile_id"),
                    "opportunity": opp,
                    "awards": awards_for_context,
                },
                timeout=120,
            )

            if res.ok:
                st.session_state[proposal_state_key] = res.json()
                st.success("Proposal plan generated.")
            else:
                st.error(res.text)

        except Exception as exc:
            st.error(f"Failed to generate proposal plan: {exc}")

    proposal_plan = st.session_state.get(proposal_state_key)

    if proposal_plan:
        if proposal_plan.get("error"):
            st.error(proposal_plan.get("error"))
        else:
            st.write("### Summary")
            st.write(proposal_plan.get("summary", ""))

            st.write("### Key Requirements")
            for item in proposal_plan.get("key_requirements", []):
                st.write(f"- {item}")

            st.write("### Win Themes")
            for item in proposal_plan.get("win_themes", []):
                st.write(f"- {item}")

            st.write("### Differentiators")
            for item in proposal_plan.get("differentiators", []):
                st.write(f"- {item}")

            st.write("### Risks")
            for item in proposal_plan.get("risks", []):
                st.write(f"- {item}")

            st.write("### Teaming Strategy")
            st.write(proposal_plan.get("teaming_strategy", ""))

            st.write("### Proposal Outline")
            for item in proposal_plan.get("proposal_outline", []):
                st.write(f"- {item}")

            if proposal_plan.get("missing_information"):
                st.write("### Missing Information")
                for item in proposal_plan.get("missing_information", []):
                    st.write(f"- {item}")

    if proposal_plan.get("evidence"):
        st.write("### Evidence")
        for item in proposal_plan.get("evidence", []):
            source = item.get("source", "Unknown")
            claim = item.get("claim", "")
            excerpt = item.get("excerpt", "")
            st.write(f"**Source:** {source}")
            st.write(f"- **Supports:** {claim}")
            if excerpt:
                st.write(f"- **Evidence:** {excerpt}")

    if proposal_plan.get("assumptions"):
        st.write("### Assumptions")
        for item in proposal_plan.get("assumptions", []):
            st.write(f"- {item}")
# --------------------------------------------------
# Ranked results section
# --------------------------------------------------
if results:
    st.header("Ranked Results")

    st.info(
        "AI scores and prioritizes the strongest candidates first. "
        "Lower-ranked or unscored opportunities remain visible for human review."
    )

    col_score, col_stage, col_display = st.columns(3)

    with col_score:
        min_score = st.slider("Minimum AI Score", min_value=0, max_value=10, value=0)

    with col_stage:
        stage_filter = st.selectbox(
            "Pursuit Stage",
            ["All", "Bid Now", "Monitor", "Market Research", "Low Priority"],
        )

    with col_display:
        max_results = st.slider("Max Results to Display", min_value=10, max_value=100, value=50)

    filtered_results = [opp for opp in results if opp.get("score", 0) >= min_score]

    if stage_filter != "All":
        filtered_results = [opp for opp in filtered_results if opp.get("stage") == stage_filter]

    st.caption(f"Results after filtering: {len(filtered_results)}")

    if not filtered_results:
        st.warning("No opportunities meet the current filters. Lower the score or change the pursuit stage.")

    for opp in filtered_results[:max_results]:
        notice_id = opp.get("notice_id", "UNKNOWN")
        existing_review = review_map.get(notice_id)
        review_label = f" | Review: {existing_review['disposition']}" if existing_review else ""
        stage = opp.get("stage", "Unknown")

        with st.expander(
            f"{opp.get('title', 'Untitled Opportunity')} | Score: {opp.get('score', 0)} | Stage: {stage}{review_label}"
        ):
            render_opportunity_tools(opp, prefix="main")


# --------------------------------------------------
# Reviewed opportunity manager
# --------------------------------------------------
st.header("Reviewed Opportunity Manager")

if not st.session_state.get("profile_id"):
    st.caption("Load a profile to view reviewed opportunities.")
else:
    if st.button("Load Reviewed Opportunities"):
        fetch_saved_reviews()

        notice_ids = [r["notice_id"] for r in st.session_state.get("reviews", [])]

        if notice_ids:
            res = requests.post(
                f"{API}/opportunities/by-ids",
                json={"notice_ids": notice_ids},
                timeout=30,
            )

            if res.ok:
                st.session_state["reviewed_opps"] = res.json()
            else:
                st.error(res.text)

    reviewed_opps = st.session_state.get("reviewed_opps", [])
    reviews = st.session_state.get("reviews", [])

    manager_review_map = {r["notice_id"]: r for r in reviews}

    if reviewed_opps:
        filter_choice = st.selectbox(
            "Filter Reviewed Opportunities",
            ["All", "Good Fit", "Maybe", "Bad Fit"],
        )

        visible = []
        for opp in reviewed_opps:
            review = manager_review_map.get(opp["notice_id"])
            if not review:
                continue

            if filter_choice == "All" or review["disposition"] == filter_choice:
                visible.append((opp, review))

        st.caption(f"{len(visible)} reviewed opportunities")

        for opp, review in visible:
            with st.expander(f"{opp['title']} | {review['disposition']}"):
                if st.button("Reload Into Ranked Results", key=f"reviewed_reanalyze_{opp['notice_id']}"):
                    res = requests.post(
                        f"{API}/opportunities/rerank",
                        json={
                            "profile_id": st.session_state.get("profile_id"),
                            "opportunities": [opp],
                        },
                        timeout=60,
                    )

                    if res.ok:
                        st.session_state["opportunities"] = res.json()
                        st.success("Re-analyzed and loaded above")
                    else:
                        st.error(res.text)

                render_opportunity_tools(opp, prefix="reviewed")
    else:
        st.caption("No reviewed opportunities loaded yet.")