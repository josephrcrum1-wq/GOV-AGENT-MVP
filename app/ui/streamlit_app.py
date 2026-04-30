import os
import requests
import streamlit as st

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


def save_analysis_output(profile_id, notice_id, analysis_type, payload):
    if not profile_id or not notice_id or not analysis_type or not payload:
        return

    try:
        requests.post(
            f"{API}/analysis/save",
            json={
                "profile_id": profile_id,
                "notice_id": notice_id,
                "analysis_type": analysis_type,
                "payload": payload,
            },
            timeout=30,
        )
    except Exception:
        pass


def load_saved_analysis_into_session(profile_id, notice_id, prefix):
    if not profile_id or not notice_id:
        return {}

    try:
        res = requests.get(f"{API}/analysis/{profile_id}/{notice_id}", timeout=30)

        if not res.ok:
            st.error(res.text)
            return {}

        saved = res.json() or {}

        key_map = {
            "decision_analysis": f"{prefix}_decision_analysis_{notice_id}",
            "proposal_plan": f"{prefix}_proposal_plan_{notice_id}",
            "proposal_draft": f"{prefix}_proposal_draft_{notice_id}",
            "advisor_review": f"{prefix}_proposal_review_{notice_id}",
            "requirements": f"{prefix}_requirements_{notice_id}",
            "compliance_matrix": f"{prefix}_compliance_matrix_{notice_id}",
            "final_review": f"{prefix}_final_review_{notice_id}",
        }

        for analysis_type, state_key in key_map.items():
            if analysis_type in saved:
                st.session_state[state_key] = saved[analysis_type].get("payload", {})

        return saved

    except Exception as exc:
        st.error(f"Failed to load saved work: {exc}")
        return {}


def render_enrichment_form(notice_id):
    profile_id = st.session_state.get("profile_id")
    enrichment_state_key = f"enrichment_{profile_id}_{notice_id}"

    if enrichment_state_key not in st.session_state:
        st.session_state[enrichment_state_key] = load_enrichment(profile_id, notice_id)

    enrichment = st.session_state.get(enrichment_state_key, {}) or {}

    st.subheader("Human Opportunity Enrichment")
    st.caption(
        "Add known contract details here before running AI analysis or proposal support. "
        "This reduces speculation and improves decision quality."
    )

    with st.form(f"enrichment_form_{notice_id}"):
        known_requirements = st.text_area("Known Requirements", value=enrichment.get("known_requirements", ""), key=f"known_requirements_{notice_id}")
        compliance_requirements = st.text_area("Compliance Requirements", value=enrichment.get("compliance_requirements", ""), key=f"compliance_requirements_{notice_id}")
        place_of_performance = st.text_input("Place of Performance", value=enrichment.get("place_of_performance", ""), key=f"place_of_performance_{notice_id}")
        clearance_requirements = st.text_input("Clearance Requirements", value=enrichment.get("clearance_requirements", ""), key=f"clearance_requirements_{notice_id}")
        deliverables = st.text_area("Deliverables", value=enrichment.get("deliverables", ""), key=f"deliverables_{notice_id}")
        period_of_performance = st.text_input("Period of Performance", value=enrichment.get("period_of_performance", ""), key=f"period_of_performance_{notice_id}")
        incumbent_or_competitors = st.text_area("Incumbent / Known Competitors", value=enrichment.get("incumbent_or_competitors", ""), key=f"incumbent_or_competitors_{notice_id}")
        submission_deadline = st.text_input("Submission Deadline", value=enrichment.get("submission_deadline", ""), key=f"submission_deadline_{notice_id}")
        customer_priorities = st.text_area("Customer Priorities", value=enrichment.get("customer_priorities", ""), key=f"customer_priorities_{notice_id}")
        questions_or_unknowns = st.text_area("Questions / Unknowns", value=enrichment.get("questions_or_unknowns", ""), key=f"questions_or_unknowns_{notice_id}")
        additional_notes = st.text_area("Additional Notes", value=enrichment.get("additional_notes", ""), key=f"additional_notes_{notice_id}")

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
    agencies_of_interest = st.text_input("Agencies of Interest (comma separated)", value=st.session_state["agencies_of_interest"])
    geographic_preferences = st.text_input("Geographic Preferences", value=st.session_state["geographic_preferences"])
    past_performance_summary = st.text_area("Past Performance Summary", value=st.session_state["past_performance_summary"])

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
                res = requests.post(f"{API}/opportunities/sync/{profile_id}", timeout=120)

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
                res = requests.post(f"{API}/opportunities/local-search", json={"profile_id": profile_id}, timeout=120)

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
                res = requests.post(f"{API}/opportunities/search", json={"profile_id": profile_id}, timeout=120)

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
# Opportunity workspace renderer
# --------------------------------------------------
def render_opportunity_tools(opp, prefix="main"):
    notice_id = opp.get("notice_id", "UNKNOWN")
    stage = opp.get("stage", "Unknown")
    existing_review = get_review_map().get(notice_id)
    profile_id = st.session_state.get("profile_id")

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

    st.markdown("---")
    st.subheader("Saved Work")

    col_load_saved, col_saved_status = st.columns([1, 3])

    with col_load_saved:
        if st.button("Load Saved Work", key=f"{prefix}_load_saved_work_{notice_id}"):
            saved = load_saved_analysis_into_session(profile_id, notice_id, prefix)
            if saved:
                st.success("Saved work loaded.")
            else:
                st.info("No saved work found yet.")

    with col_saved_status:
        st.caption("Saved outputs are stored by profile, notice ID, and analysis type. Re-running an analysis overwrites the saved version.")

    overview_tab, docs_tab, req_tab, decision_tab, proposal_tab, compliance_tab, advisor_tab, export_tab = st.tabs(
        [
            "Overview",
            "Documents",
            "Requirements",
            "Decision",
            "Proposal",
            "Compliance",
            "Advisor Review",
            "Export",
        ]
    )

    # --------------------------------------------------
    # Overview tab
    # --------------------------------------------------
    with overview_tab:
        render_enrichment_form(notice_id)

        st.markdown("---")
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
    # Documents tab
    # --------------------------------------------------
    with docs_tab:
        st.subheader("Document Intelligence")
        st.caption("Shows whether solicitation documents were captured, extracted, and available for AI analysis.")

        docs_key = f"{prefix}_documents_{notice_id}"

        if docs_key not in st.session_state:
            try:
                res = requests.get(f"{API}/documents/{notice_id}", timeout=30)
                if res.ok:
                    st.session_state[docs_key] = res.json()
                else:
                    st.session_state[docs_key] = []
            except Exception:
                st.session_state[docs_key] = []

        col_load_docs, col_process_docs, col_process_reviewed = st.columns(3)

        with col_load_docs:
            if st.button("Load Documents", key=f"{prefix}_load_docs_{notice_id}"):
                try:
                    res = requests.get(f"{API}/documents/{notice_id}", timeout=30)

                    if res.ok:
                        st.session_state[docs_key] = res.json()
                        st.success("Documents loaded.")
                    else:
                        st.error(res.text)

                except Exception as exc:
                    st.error(f"Failed to load documents: {exc}")

        with col_process_docs:
            if st.button("Process Pending Documents", key=f"{prefix}_process_docs_{notice_id}"):
                try:
                    res = requests.post(f"{API}/documents/process?limit=10", timeout=120)

                    if res.ok:
                        st.success(f"Processing result: {res.json()}")
                    else:
                        st.error(res.text)

                except Exception as exc:
                    st.error(f"Failed to process documents: {exc}")

        with col_process_reviewed:
            if st.button("Process Reviewed Docs", key=f"{prefix}_process_reviewed_docs_{notice_id}"):
                try:
                    if not profile_id:
                        st.error("Load a profile first.")
                    else:
                        res = requests.post(f"{API}/documents/process-reviewed/{profile_id}?limit=10", timeout=120)

                        if res.ok:
                            st.success(f"Reviewed document processing result: {res.json()}")
                        else:
                            st.error(res.text)

                except Exception as exc:
                    st.error(f"Failed to process reviewed documents: {exc}")

        documents = st.session_state.get(docs_key, [])

        if documents:
            complete_docs = [d for d in documents if d.get("extraction_status") == "complete"]
            total_text = sum(d.get("text_length", 0) for d in documents)

            dcol1, dcol2, dcol3 = st.columns(3)

            with dcol1:
                st.metric("Documents Found", len(documents))

            with dcol2:
                st.metric("Extracted", len(complete_docs))

            with dcol3:
                st.metric("Total Text Chars", total_text)

            for doc in documents:
                st.markdown("---")
                st.write(f"**Name:** {doc.get('document_name', '')}")
                st.write(f"**Status:** {doc.get('extraction_status', '')}")
                st.write(f"**Text Length:** {doc.get('text_length', 0)}")

                url = doc.get("document_url", "")
                if url:
                    st.markdown(f"[Open Source Link]({url})")

                if doc.get("error_message"):
                    st.error(doc.get("error_message"))

                if doc.get("text_preview"):
                    with st.expander("Preview Extracted Text"):
                        st.write(doc.get("text_preview"))
        else:
            st.warning("No documents loaded for this opportunity. AI analysis may rely only on SAM metadata and human enrichment.")

        st.markdown("---")
        st.subheader("Manual Document Upload")
        st.caption("Upload RFP, SOW, PWS, amendment, or contracting office documents received outside SAM.gov. Supported: PDF, DOCX, TXT.")

        uploaded_file = st.file_uploader(
            "Upload solicitation document",
            type=["pdf", "docx", "txt"],
            key=f"{prefix}_manual_upload_{notice_id}",
        )

        if uploaded_file:
            if st.button("Upload and Extract Document", key=f"{prefix}_submit_manual_upload_{notice_id}"):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/octet-stream",
                        )
                    }

                    res = requests.post(
                        f"{API}/documents/upload?notice_id={notice_id}",
                        files=files,
                        timeout=120,
                    )

                    if res.ok:
                        st.success(f"Upload result: {res.json()}")

                        docs_res = requests.get(f"{API}/documents/{notice_id}", timeout=30)
                        if docs_res.ok:
                            st.session_state[docs_key] = docs_res.json()
                    else:
                        st.error(res.text)

                except Exception as exc:
                    st.error(f"Manual upload failed: {exc}")

    # --------------------------------------------------
    # Requirements tab
    # --------------------------------------------------
    with req_tab:
        st.subheader("Requirement Extraction")
        st.caption("Extracts requirements from uploaded/captured documents.")

        requirements_key = f"{prefix}_requirements_{notice_id}"

        if st.button("Extract Requirements", key=f"{prefix}_extract_requirements_{notice_id}"):
            try:
                res = requests.post(
                    f"{API}/requirements/extract",
                    json={"opportunity": opp},
                    timeout=120,
                )

                if res.ok:
                    result = res.json()
                    st.session_state[requirements_key] = result
                    save_analysis_output(profile_id, notice_id, "requirements", result)
                    st.success("Requirements extracted and saved.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to extract requirements: {exc}")

        requirements_result = st.session_state.get(requirements_key) or {}

        if isinstance(requirements_result, dict) and requirements_result:
            requirements = requirements_result.get("requirements", [])

            st.write(f"### Extracted Requirements ({len(requirements)})")

            if requirements:
                for req in requirements:
                    with st.expander(f"{req.get('id', '')} | {req.get('category', '').title()} | {req.get('priority', '').title()}"):
                        st.write(f"**Requirement:** {req.get('requirement', '')}")
                        st.write(f"**Source Document:** {req.get('source_document', 'Unknown')}")
                        st.write(f"**Ambiguity:** {req.get('ambiguity', '')}")
                        st.write(f"**Source Excerpt:** {req.get('source_excerpt', '')}")
            else:
                st.warning("No requirements extracted.")

            if requirements_result.get("missing_information"):
                st.write("### Requirement Extraction Gaps")
                for item in requirements_result.get("missing_information", []):
                    st.write(f"- {item}")

    # --------------------------------------------------
    # Decision tab
    # --------------------------------------------------
    with decision_tab:
        st.subheader("Historical Award Analysis")

        awards_state_key = f"{prefix}_similar_awards_{notice_id}"
        awards_summary_key = f"{prefix}_similar_awards_summary_{notice_id}"
        awards_comparison_key = f"{prefix}_similar_awards_comparison_{notice_id}"

        if st.button("Find Similar Awards", key=f"{prefix}_find_awards_button_{notice_id}"):
            try:
                res = requests.post(
                    f"{API}/awards/similar",
                    json={
                        "profile_id": profile_id,
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

        st.markdown("---")
        st.subheader("Full AI Decision Analysis")

        decision_state_key = f"{prefix}_decision_analysis_{notice_id}"

        if st.button("Run / Reanalyze Full AI Analysis", key=f"{prefix}_decision_button_{notice_id}"):
            try:
                awards_for_context = st.session_state.get(awards_state_key, [])

                res = requests.post(
                    f"{API}/decision/analyze",
                    json={
                        "profile_id": profile_id,
                        "opportunity": opp,
                        "awards": awards_for_context,
                    },
                    timeout=120,
                )

                if res.ok:
                    result = res.json()
                    st.session_state[decision_state_key] = result
                    save_analysis_output(profile_id, notice_id, "decision_analysis", result)
                    st.success("Decision analysis complete and saved.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to run decision analysis: {exc}")

        decision = st.session_state.get(decision_state_key) or {}

        if isinstance(decision, dict) and decision:
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
                    st.write(f"**Source:** {item.get('source', 'Unknown')}")
                    st.write(f"- **Supports:** {item.get('claim', '')}")
                    if item.get("excerpt"):
                        st.write(f"- **Evidence:** {item.get('excerpt')}")

            if decision.get("assumptions"):
                st.write("### Assumptions")
                for item in decision.get("assumptions", []):
                    st.write(f"- {item}")

    # --------------------------------------------------
    # Proposal tab
    # --------------------------------------------------
    with proposal_tab:
        st.subheader("Proposal Support")

        proposal_state_key = f"{prefix}_proposal_plan_{notice_id}"

        if st.button("Generate / Reanalyze Proposal Plan", key=f"{prefix}_proposal_button_{notice_id}"):
            try:
                awards_for_context = st.session_state.get(f"{prefix}_similar_awards_{notice_id}", [])

                res = requests.post(
                    f"{API}/proposal/plan",
                    json={
                        "profile_id": profile_id,
                        "opportunity": opp,
                        "awards": awards_for_context,
                    },
                    timeout=120,
                )

                if res.ok:
                    result = res.json()
                    st.session_state[proposal_state_key] = result
                    save_analysis_output(profile_id, notice_id, "proposal_plan", result)
                    st.success("Proposal plan generated and saved.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to generate proposal plan: {exc}")

        proposal_plan = st.session_state.get(proposal_state_key) or {}

        if isinstance(proposal_plan, dict) and proposal_plan:
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
                        st.write(f"**Source:** {item.get('source', 'Unknown')}")
                        st.write(f"- **Supports:** {item.get('claim', '')}")
                        if item.get("excerpt"):
                            st.write(f"- **Evidence:** {item.get('excerpt')}")

                if proposal_plan.get("assumptions"):
                    st.write("### Assumptions")
                    for item in proposal_plan.get("assumptions", []):
                        st.write(f"- {item}")

        st.markdown("---")
        st.subheader("Full Proposal Draft")

        proposal_draft_key = f"{prefix}_proposal_draft_{notice_id}"

        if st.button("Generate / Reanalyze Full Proposal", key=f"{prefix}_proposal_draft_btn_{notice_id}"):
            try:
                res = requests.post(
                    f"{API}/proposal/full",
                    json={
                        "profile_id": profile_id,
                        "opportunity": opp,
                        "proposal_plan": proposal_plan,
                    },
                    timeout=120,
                )

                if res.ok:
                    result = res.json()
                    st.session_state[proposal_draft_key] = result
                    save_analysis_output(profile_id, notice_id, "proposal_draft", result)
                    st.success("Full proposal draft generated and saved.")
                else:
                    st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to generate proposal: {exc}")

        draft = st.session_state.get(proposal_draft_key) or {}

        if isinstance(draft, dict) and draft:
            st.write("## Executive Summary")
            st.write(draft.get("executive_summary", ""))

            st.write("## Technical Approach")
            st.write(draft.get("technical_approach", ""))

            st.write("## Management Plan")
            st.write(draft.get("management_plan", ""))

            st.write("## Past Performance")
            st.write(draft.get("past_performance", ""))

            st.write("## Staffing Plan")
            st.write(draft.get("staffing_plan", ""))

            if draft.get("assumptions"):
                st.write("## Assumptions")
                for item in draft.get("assumptions", []):
                    st.write(f"- {item}")

            if draft.get("missing_information"):
                st.write("## Missing Information")
                for item in draft.get("missing_information", []):
                    st.write(f"- {item}")

    # --------------------------------------------------
    # Compliance tab
    # --------------------------------------------------
    with compliance_tab:
        st.subheader("Compliance Matrix")

        requirements_key = f"{prefix}_requirements_{notice_id}"
        compliance_key = f"{prefix}_compliance_matrix_{notice_id}"

        requirements_result = st.session_state.get(requirements_key) or {}

        if st.button("Build / Rebuild Compliance Matrix", key=f"{prefix}_build_matrix_{notice_id}"):
            try:
                proposal_draft = st.session_state.get(f"{prefix}_proposal_draft_{notice_id}") or {}
                review = st.session_state.get(f"{prefix}_proposal_review_{notice_id}") or {}
                revised_proposal = {}

                if isinstance(review, dict):
                    revised_proposal = review.get("revised_proposal", {}) or {}

                if not requirements_result:
                    st.error("Extract requirements first.")
                elif not proposal_draft and not revised_proposal:
                    st.error("Generate a proposal draft or senior advisor revision first.")
                else:
                    res = requests.post(
                        f"{API}/requirements/compliance-matrix",
                        json={
                            "opportunity": opp,
                            "requirements_result": requirements_result,
                            "proposal_draft": proposal_draft,
                            "revised_proposal": revised_proposal,
                        },
                        timeout=120,
                    )

                    if res.ok:
                        result = res.json()
                        st.session_state[compliance_key] = result
                        save_analysis_output(profile_id, notice_id, "compliance_matrix", result)
                        st.success("Compliance matrix generated and saved.")
                    else:
                        st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to build compliance matrix: {exc}")

        compliance = st.session_state.get(compliance_key) or {}

        if isinstance(compliance, dict) and compliance:
            st.write("### Compliance Readiness")
            st.write(f"**Overall Status:** {compliance.get('overall_status', '')}")
            st.write(compliance.get("summary", ""))

            matrix = compliance.get("matrix", [])

            if matrix:
                st.write("### Compliance Matrix")

                for row in matrix:
                    with st.expander(f"{row.get('requirement_id', '')} | {row.get('category', '').title()} | {row.get('status', '')}"):
                        st.write(f"**Requirement:** {row.get('requirement', '')}")
                        st.write(f"**Source Document:** {row.get('source_document', 'Unknown')}")
                        st.write(f"**Source Excerpt:** {row.get('source_excerpt', '')}")
                        st.write(f"**Proposal Section:** {row.get('proposal_section', '')}")
                        st.write(f"**Evidence From Proposal:** {row.get('evidence_from_proposal', '')}")
                        st.write(f"**Gap:** {row.get('gap', '')}")
                        st.write(f"**Recommended Fix:** {row.get('recommended_fix', '')}")

            if compliance.get("major_gaps"):
                st.write("### Major Gaps")
                for item in compliance.get("major_gaps", []):
                    st.write(f"- {item}")

            if compliance.get("unsupported_claims"):
                st.write("### Unsupported Claims")
                for item in compliance.get("unsupported_claims", []):
                    st.write(f"- {item}")

            if compliance.get("recommended_next_steps"):
                st.write("### Recommended Next Steps")
                for item in compliance.get("recommended_next_steps", []):
                    st.write(f"- {item}")

    # --------------------------------------------------
    # Advisor Review tab
    # --------------------------------------------------
    with advisor_tab:
        st.subheader("Senior Capture Advisor Review")

        proposal_draft_key = f"{prefix}_proposal_draft_{notice_id}"
        proposal_review_key = f"{prefix}_proposal_review_{notice_id}"

        draft = st.session_state.get(proposal_draft_key) or {}

        if st.button("Run / Reanalyze Senior Capture Review", key=f"{prefix}_proposal_review_btn_{notice_id}"):
            try:
                proposal_plan = st.session_state.get(f"{prefix}_proposal_plan_{notice_id}") or {}

                if not draft:
                    st.error("Generate a proposal draft first.")
                else:
                    res = requests.post(
                        f"{API}/proposal/review",
                        json={
                            "profile_id": profile_id,
                            "opportunity": opp,
                            "proposal_plan": proposal_plan,
                            "proposal_draft": draft,
                        },
                        timeout=120,
                    )

                    if res.ok:
                        result = res.json()
                        st.session_state[proposal_review_key] = result
                        save_analysis_output(profile_id, notice_id, "advisor_review", result)
                        st.success("Senior capture review complete and saved.")
                    else:
                        st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to run senior capture review: {exc}")

        review = st.session_state.get(proposal_review_key) or {}

        if isinstance(review, dict) and review:
            st.write("### Overall Assessment")
            st.write(review.get("overall_assessment", ""))

            st.write("### Screening Risks")
            for item in review.get("screening_risks", []):
                st.write(f"- {item}")

            st.write("### Compliance Gaps")
            for item in review.get("compliance_gaps", []):
                st.write(f"- {item}")

            st.write("### Section Feedback")
            section_feedback = review.get("section_feedback", {})
            if isinstance(section_feedback, dict):
                for section, feedback in section_feedback.items():
                    st.write(f"**{section.replace('_', ' ').title()}:** {feedback}")

            st.write("### Recommended Revisions")
            for item in review.get("recommended_revisions", []):
                st.write(f"- {item}")

            revised = review.get("revised_proposal", {})
            if isinstance(revised, dict) and revised:
                st.write("### Revised Proposal Draft")

                for section in ["executive_summary", "technical_approach", "management_plan", "past_performance", "staffing_plan"]:
                    st.write(f"#### {section.replace('_', ' ').title()}")
                    st.write(revised.get(section, ""))

            if review.get("assumptions"):
                st.write("### Assumptions")
                for item in review.get("assumptions", []):
                    st.write(f"- {item}")

            if review.get("missing_information"):
                st.write("### Missing Information")
                for item in review.get("missing_information", []):
                    st.write(f"- {item}")

        st.markdown("---")
        st.subheader("Final Review After Compliance Matrix")

        final_review_key = f"{prefix}_final_review_{notice_id}"

        if st.button("Run Final Review After Compliance Matrix", key=f"{prefix}_final_review_btn_{notice_id}"):
            try:
                proposal_draft = st.session_state.get(f"{prefix}_proposal_draft_{notice_id}") or {}
                advisor_review = st.session_state.get(f"{prefix}_proposal_review_{notice_id}") or {}
                compliance_matrix = st.session_state.get(f"{prefix}_compliance_matrix_{notice_id}") or {}

                if not proposal_draft:
                    st.error("Generate a proposal draft first.")
                elif not advisor_review:
                    st.error("Run Senior Capture Review first.")
                elif not compliance_matrix:
                    st.error("Build Compliance Matrix first.")
                else:
                    res = requests.post(
                        f"{API}/proposal/final-review",
                        json={
                            "profile_id": profile_id,
                            "opportunity": opp,
                            "proposal_draft": proposal_draft,
                            "advisor_review": advisor_review,
                            "compliance_matrix": compliance_matrix,
                        },
                        timeout=120,
                    )

                    if res.ok:
                        result = res.json()
                        st.session_state[final_review_key] = result
                        save_analysis_output(profile_id, notice_id, "final_review", result)
                        st.success("Final compliance-based review complete and saved.")
                    else:
                        st.error(res.text)

            except Exception as exc:
                st.error(f"Failed to run final review: {exc}")

        final_review = st.session_state.get(final_review_key) or {}

        if isinstance(final_review, dict) and final_review:
            st.write("### Final Readiness Assessment")
            st.write(final_review.get("final_readiness_assessment", ""))

            st.write(f"**Readiness Score:** {final_review.get('proposal_readiness_score', 0)} / 100")

            st.write("### Highest Priority Fixes")
            for item in final_review.get("highest_priority_fixes", []):
                st.write(f"- {item}")

            revisions = final_review.get("compliance_driven_revisions", {})
            if isinstance(revisions, dict) and revisions:
                st.write("### Compliance-Driven Revisions")
                for section, text in revisions.items():
                    st.write(f"#### {section.replace('_', ' ').title()}")
                    st.write(text)

            st.write("### Remaining Compliance Risks")
            for item in final_review.get("remaining_compliance_risks", []):
                st.write(f"- {item}")

            st.write("### Remaining Unsupported Claims")
            for item in final_review.get("remaining_unsupported_claims", []):
                st.write(f"- {item}")

            st.write("### Recommended Next Steps")
            for item in final_review.get("recommended_next_steps", []):
                st.write(f"- {item}")

    # --------------------------------------------------
    # Export tab
    # --------------------------------------------------
    with export_tab:
        st.subheader("Export")

        review = st.session_state.get(f"{prefix}_proposal_review_{notice_id}") or {}
        final_review = st.session_state.get(f"{prefix}_final_review_{notice_id}") or {}

        revised_for_export = {}

        if isinstance(final_review, dict) and final_review.get("compliance_driven_revisions"):
            revised_for_export = final_review.get("compliance_driven_revisions", {}) or {}
            export_review_payload = final_review
            st.info("Export will use final compliance-driven revisions.")
        elif isinstance(review, dict) and review.get("revised_proposal"):
            revised_for_export = review.get("revised_proposal", {}) or {}
            export_review_payload = review
            st.info("Export will use senior advisor revised proposal.")
        else:
            export_review_payload = {}
            st.warning("Run Senior Capture Review or Final Review before exporting.")

        if isinstance(revised_for_export, dict) and revised_for_export:
            download_key = f"{prefix}_proposal_docx_{notice_id}"

            if st.button("Prepare Word Document", key=f"{prefix}_prepare_docx_{notice_id}"):
                try:
                    export_res = requests.post(
                        f"{API}/proposal/export-docx",
                        json={
                            "revised_proposal": revised_for_export,
                            "review": export_review_payload,
                        },
                        timeout=120,
                    )

                    if export_res.ok:
                        st.session_state[download_key] = export_res.content
                        st.success("Document ready for download.")
                    else:
                        st.error("Failed to generate Word document.")

                except Exception as exc:
                    st.error(f"Export failed: {exc}")

            docx_data = st.session_state.get(download_key)

            if docx_data:
                st.download_button(
                    label="Download Revised Proposal as Word Document",
                    data=docx_data,
                    file_name="revised_proposal_draft.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"{prefix}_download_docx_{notice_id}",
                )


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
        else:
            st.session_state["reviewed_opps"] = []
            st.info("No reviewed opportunities found.")

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