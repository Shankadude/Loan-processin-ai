import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(
    page_title="AI Loan Underwriting Workbench",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 10px;
    }
    .badge-approved { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-review { background-color: #fff3e0; color: #ef6c00; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-rejected { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-incomplete { background-color: #fff8e1; color: #f57f17; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://127.0.0.1:8000"

# --- Session State Setup ---
if "application_results" not in st.session_state:
    st.session_state.application_results = None
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

st.sidebar.title("🏦 Underwriting Ops")
nav_selection = st.sidebar.radio("Navigation", ["Application Intake", "Audit & Analytics"])

# ==========================================
# PAGE 1: INTAKE & VERIFICATION WORKBENCH
# ==========================================
if nav_selection == "Application Intake":
    st.title("📄 AI-Powered Loan Document Ingestion")
    st.caption("Upload loan application files (PDF/Images) for automated multimodal extraction, incompleteness validation, and underwriting.")

    # Top Parameters Bar
    with st.container():
        col_inc, col_amt = st.columns(2)
        with col_inc:
            declared_income = st.number_input("Declared Monthly Income (₹)", min_value=1000.0, value=95000.0, step=5000.0)
        with col_amt:
            requested_amount = st.number_input("Requested Loan Amount (₹)", min_value=10000.0, value=500000.0, step=25000.0)

    # Multi-file Uploader
    uploaded_files = st.file_uploader(
        "Upload Borrower Documents (KYC, Salary Slips, Bank Statements, Tax Returns)",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🚀 Process Full Loan Package", type="primary", disabled=st.session_state.is_processing):
            st.session_state.is_processing = True
            with st.spinner("Executing Pipeline: Classifying, Extracting & Validating Completeness..."):
                multipart_files = [
                    ("files", (file.name, file.getvalue(), file.type)) 
                    for file in uploaded_files
                ]
                data_payload = {
                    "declared_income": declared_income,
                    "requested_amount": requested_amount
                }

                try:
                    res = requests.post(
                        f"{API_BASE_URL}/applications",
                        data=data_payload,
                        files=multipart_files
                    )
                    if res.status_code == 200:
                        st.session_state.application_results = res.json()
                        st.success("✅ Application successfully processed!")
                    else:
                        st.error(f"Error {res.status_code}: {res.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🚫 Backend unreachable. Make sure FastAPI is running on port 8000.")

            st.session_state.is_processing = False
            st.rerun()

    # --- Underwriter Review Dashboard ---
    if st.session_state.application_results:
        results = st.session_state.application_results
        decision = results.get("underwriting_decision", {})
        decision_res = results.get("validation_report") or results.get("decision_result", {})
        app_id = results.get("application_id")
        app_status = results.get("status", "UNKNOWN")
        missing_docs = results.get("missing_documents", [])

        st.markdown("---")
        st.header("📋 Underwriting Executive Summary")
        st.info(f"**Application ID:** `{app_id}`")

        # Missing Documents Alert Banner
        if app_status == "INCOMPLETE" or missing_docs:
            st.warning(f"⚠️ **Incomplete Application Package:** Missing mandatory document(s): `{', '.join(missing_docs)}`")
            
            # Incremental Document Upload Section
            with st.expander("➕ Upload Additional Missing Documents to this Application", expanded=True):
                incremental_files = st.file_uploader(
                    "Select additional files to append:",
                    type=["pdf", "png", "jpg", "jpeg"],
                    accept_multiple_files=True,
                    key="incremental_file_uploader"
                )
                if incremental_files and st.button("📤 Append Documents to Application"):
                    with st.spinner("Appending new files and re-evaluating application..."):
                        inc_multipart = [
                            ("files", (file.name, file.getvalue(), file.type))
                            for file in incremental_files
                        ]
                        try:
                            inc_res = requests.post(
                                f"{API_BASE_URL}/applications/{app_id}/documents",
                                files=inc_multipart
                            )
                            if inc_res.status_code == 200:
                                st.session_state.application_results = inc_res.json()
                                st.success("✅ Documents appended and package re-evaluated!")
                                st.rerun()
                            else:
                                st.error(f"Error: {inc_res.text}")
                        except requests.exceptions.ConnectionError:
                            st.error("🚫 Backend unreachable.")

        # Top Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        verdict = decision.get("verdict", "UNKNOWN")
        dti_val = decision_res.get("dti_percent", decision_res.get("calculated_dti", 0.0))
        risk_lvl = decision_res.get("risk_level", decision_res.get("dti_risk_level", "N/A"))
        inc_variance = decision_res.get("income_difference_percent", decision_res.get("income_variance_pct", 0.0))
        risk_score = decision_res.get("risk_score", 0)

        with m1:
            st.markdown("**Underwriting Verdict**")
            if verdict == "APPROVED":
                st.markdown("<span class='badge-approved'>APPROVED</span>", unsafe_allow_html=True)
            elif verdict == "CONDITIONALLY_APPROVED":
                st.markdown("<span class='badge-review'>CONDITIONALLY APPROVED</span>", unsafe_allow_html=True)
            elif verdict == "REJECTED":
                st.markdown("<span class='badge-rejected'>REJECTED</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span class='badge-incomplete'>{app_status}</span>", unsafe_allow_html=True)

        with m2:
            st.metric("Calculated DTI", f"{dti_val:.1f}%", f"Risk: {risk_lvl}")
        with m3:
            st.metric("Income Variance", f"{inc_variance:.1f}%")
        with m4:
            st.metric("Risk Penalty Score", f"{risk_score}/100")

        # Executive Rationale & Flags
        if decision.get("executive_rationale"):
            st.markdown(f"**Executive Rationale:** {decision.get('executive_rationale')}")

        if decision.get("conditions"):
            st.warning("⚠️ **Approval Conditions:**\n" + "\n".join([f"- {c}" for c in decision["conditions"]]))
        if decision.get("adverse_action_reasons"):
            st.error("❌ **Adverse Action Reasons:**\n" + "\n".join([f"- {r}" for r in decision["adverse_action_reasons"]]))

        # Anomaly Findings Section
        anomalies = decision_res.get("anomalies", [])
        if anomalies:
            st.markdown("##### 🚨 Policy Anomalies Detected")
            for anom in anomalies:
                st.warning(f"**[{anom.get('code')}]** ({anom.get('severity')} Severity): {anom.get('description')}")

        # Individual Document Inspection (HITL)
        st.markdown("---")
        st.subheader("📑 Document Verification & Human Review")
        
        docs = results.get("extracted_documents", [])
        if not docs:
            st.info("No documents parsed yet.")
            
        for i, doc in enumerate(docs):
            filename = doc.get("filename")
            doc_type = doc.get("document_type") or doc.get("doc_type", "UNKNOWN")
            confidence = doc.get("confidence", 1.0) * 100
            extracted = doc.get("extracted_data") or doc.get("extracted", {})

            with st.expander(f"**{doc_type}** — `{filename}` (Confidence: {confidence:.1f}%)"):
                with st.form(key=f"form_doc_{i}"):
                    st.markdown("##### Extracted Field Editor")
                    edited_fields = {}

                    cols = st.columns(2)
                    for idx, (field_name, field_val) in enumerate(extracted.items()):
                        target_col = cols[idx % 2]
                        edited_fields[field_name] = target_col.text_input(
                            label=field_name.replace("_", " ").title(),
                            value=str(field_val) if field_val is not None else "",
                            key=f"{app_id}_{i}_{field_name}"
                        )

                    save_btn = st.form_submit_button("💾 Save Verified Document Data")
                    if save_btn:
                        payload = {
                            "application_id": app_id,
                            "filename": filename,
                            "original_extracted_data": extracted,
                            "verified_data": edited_fields
                        }
                        try:
                            save_res = requests.post(f"{API_BASE_URL}/api/save-verified-document/", json=payload)
                            if save_res.status_code == 200:
                                st.success(f"✅ Verified data for `{filename}` committed to MongoDB!")
                            else:
                                st.error(f"Failed to save: {save_res.text}")
                        except requests.exceptions.ConnectionError:
                            st.error("🚫 Backend unreachable.")

# ==========================================
# PAGE 2: AUDIT & HISTORICAL ANALYTICS
# ==========================================
elif nav_selection == "Audit & Analytics":
    st.title("📊 Loan Processing History & Compliance Audit")
    st.caption("Inspect persisted records from MongoDB for compliance checks and data reconciliation.")
    
    search_app_id = st.text_input("Enter Application ID to inspect (e.g., APP-xxxx):")
    if search_app_id and st.button("🔍 Search Record"):
        try:
            lookup_res = requests.get(f"{API_BASE_URL}/applications/{search_app_id.strip()}")
            if lookup_res.status_code == 200:
                record = lookup_res.json()
                st.success(f"✅ Application `{search_app_id}` Found!")
                st.json(record)
            else:
                st.error("Application not found in database.")
        except requests.exceptions.ConnectionError:
            st.error("🚫 Backend unreachable.")