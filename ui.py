import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(
    page_title="Intelligent Loan Underwriting Workbench",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Professional Banking Workbench Styling ---
st.markdown("""
<style>
    .reportview-container { background: #fdfdfd; }
    .metric-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e0e0e0;
        margin-bottom: 12px;
    }
    .badge-approved { background-color: #e8f5e9; color: #2e7d32; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #a5d6a7; display: inline-block; }
    .badge-review { background-color: #fff3e0; color: #ef6c00; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #ffcc80; display: inline-block; }
    .badge-rejected { background-color: #ffebee; color: #c62828; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #ef9a9a; display: inline-block; }
    .badge-incomplete { background-color: #fff8e1; color: #f57f17; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #ffe082; display: inline-block; }
    
    .badge-green { background-color: #d4edda; color: #155724; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #c3e6cb; display: inline-block; }
    .badge-amber { background-color: #fff3cd; color: #856404; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #ffeeba; display: inline-block; }
    .badge-red { background-color: #f8d7da; color: #721c24; padding: 6px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #f5c6cb; display: inline-block; }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://127.0.0.1:8000"

if "application_results" not in st.session_state:
    st.session_state.application_results = None
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

st.sidebar.title("🏦 Underwriting Ops")
nav_selection = st.sidebar.radio("Navigation", ["Application Intake & Underwriting", "Audit & Analytics"])

# ==========================================
# PAGE 1: INTAKE & VERIFICATION WORKBENCH
# ==========================================
if nav_selection == "Application Intake & Underwriting":
    st.title("📄 Intelligent Loan Document Processing Engine")
    st.caption("Automated multimodal extraction, deterministic TRACE credit underwriting, forensic balance verification, and human audit.")

    # Top Parameters Bar (Optional Manual Override - Defaults to Automated Extraction from Loan Application Form)
    with st.expander("⚙️ Manual Form Overrides (Optional — Defaults to Auto-Extraction from Documents)", expanded=False):
        st.caption("Leave disabled to let the engine read Declared Income and Requested Loan Amount directly from the submitted Loan Application Form.")
        use_manual_override = st.checkbox("Enable manual parameter overrides", value=False)
        col_inc, col_amt = st.columns(2)
        with col_inc:
            declared_income = st.number_input(
                "Declared Monthly Net Income (₹)", 
                min_value=0.0, 
                value=0.0, 
                step=5000.0,
                disabled=not use_manual_override
            )
        with col_amt:
            requested_amount = st.number_input(
                "Requested Loan Amount (₹)", 
                min_value=0.0, 
                value=0.0, 
                step=25000.0,
                disabled=not use_manual_override
            )

    # Multi-file Ingestion
    uploaded_files = st.file_uploader(
        "Upload Borrower Package (PAN, Identity Proof, 3-Month Payslips, Form 16, Bank Statement)",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("🚀 Ingest & Process Loan Package", type="primary", disabled=st.session_state.is_processing):
            st.session_state.is_processing = True
            with st.spinner("Executing Pipeline: Classifying documents, verifying cross-identity, calculating math & evaluating rules..."):
                multipart_files = [
                    ("files", (file.name, file.getvalue(), file.type)) 
                    for file in uploaded_files
                ]
                data_payload = {
                    "declared_income": declared_income if use_manual_override else 0.0,
                    "requested_amount": requested_amount if use_manual_override else 0.0
                }

                try:
                    res = requests.post(
                        f"{API_BASE_URL}/applications",
                        data=data_payload,
                        files=multipart_files,
                        timeout=300
                    )
                    if res.status_code == 200:
                        st.session_state.application_results = res.json()
                        st.session_state.error_message = None
                        st.success("✅ Application package processed and evaluated successfully!")
                    else:
                        st.session_state.error_message = f"Backend Error ({res.status_code}): {res.text}"
                        st.error(st.session_state.error_message)
                except requests.exceptions.ConnectionError:
                    st.session_state.error_message = "🚫 Backend unreachable. Make sure FastAPI server is running on port 8000."
                    st.error(st.session_state.error_message)
                except Exception as ex:
                    st.session_state.error_message = f"❌ Error: {str(ex)}"
                    st.error(st.session_state.error_message)

            st.session_state.is_processing = False
            if st.session_state.application_results:
                st.rerun()

    # --- Underwriter Dashboard ---
    if st.session_state.application_results:
        results = st.session_state.application_results
        app_id = results.get("application_id", "UNKNOWN")
        app_status = results.get("status", "UNKNOWN")
        missing_docs = results.get("missing_documents", [])

        val_rep = results.get("validation_report") or {}
        underwriting = results.get("underwriting_decision") or {}

        # Nested payloads resolution
        step4_comp = val_rep.get("step4_comparison") or {}
        step5_calc = val_rep.get("step5_calculation") or {}
        step6_risk = val_rep.get("step6_risk_anomaly") or {}

        inc_metrics = step5_calc.get("income_metrics", {})
        ob_metrics = step5_calc.get("obligation_metrics", {})
        stmt_metrics = step5_calc.get("statement_validation", {})
        elig_metrics = step5_calc.get("eligibility_result", {})

        # Robust metric resolution across both flat and step structures
        dti_val = float(val_rep.get("dti_percent") if val_rep.get("dti_percent") is not None else (ob_metrics.get("dti_percent") or 0.0))
        risk_lvl = val_rep.get("risk_level") or step6_risk.get("risk_grade") or "N/A"
        inc_variance = float(val_rep.get("income_difference_percent") if val_rep.get("income_difference_percent") is not None else (inc_metrics.get("income_difference_percent") or 0.0))
        risk_score = float(val_rep.get("risk_score") if val_rep.get("risk_score") is not None else (step6_risk.get("risk_score") if step6_risk.get("risk_score") is not None else 0.0))
        routing_color = (val_rep.get("routing_color") or step6_risk.get("routing_color") or "AMBER").upper()
        routing_reason = val_rep.get("routing_reason") or step6_risk.get("routing_reason") or ""
        verdict = underwriting.get("verdict") or ("APPROVED" if routing_color == "GREEN" else ("REJECTED" if routing_color == "RED" else "REVIEW"))

        stmt_stat = val_rep.get("statement_arithmetic_status") or stmt_metrics.get("status", "NOT_AVAILABLE")
        stmt_diff = float(val_rep.get("statement_arithmetic_difference") or stmt_metrics.get("difference_amount", 0.0))

        st.markdown("---")
        st.header(f"📋 Underwriting Executive Summary — `{app_id}`")

        # Missing Document Alert Banner
        if app_status == "INCOMPLETE" or missing_docs:
            st.warning(f"⚠️ **Incomplete Document Package:** Missing mandatory document(s): `{', '.join(missing_docs)}`")
            with st.expander("➕ Incremental Document Ingestion", expanded=True):
                incremental_files = st.file_uploader(
                    "Select missing files to append to this application:",
                    type=["pdf", "png", "jpg", "jpeg"],
                    accept_multiple_files=True,
                    key="inc_uploader"
                )
                if incremental_files and st.button("📤 Upload & Re-Evaluate Package"):
                    inc_multipart = [("files", (f.name, f.getvalue(), f.type)) for f in incremental_files]
                    try:
                        inc_res = requests.post(f"{API_BASE_URL}/applications/{app_id}/documents", files=inc_multipart)
                        if inc_res.status_code == 200:
                            st.session_state.application_results = inc_res.json()
                            st.success("✅ Application updated and re-evaluated!")
                            st.rerun()
                    except Exception as err:
                        st.error(f"Error appending files: {err}")

        # Primary Key Metrics Bar
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown("**Underwriting Decision**")
            if verdict == "APPROVED":
                st.markdown("<span class='badge-approved'>APPROVED</span>", unsafe_allow_html=True)
            elif verdict == "REJECTED":
                st.markdown("<span class='badge-rejected'>REJECTED</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='badge-review'>MANUAL REVIEW</span>", unsafe_allow_html=True)
            
            st.write("")
            if routing_color == "GREEN":
                st.markdown("<span class='badge-green'>🟢 Fast-Track (STP)</span>", unsafe_allow_html=True)
            elif routing_color == "RED":
                st.markdown("<span class='badge-red'>🔴 Hard Reject</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='badge-amber'>🟡 Amber Review</span>", unsafe_allow_html=True)

        with m2:
            foir_assess = step5_calc.get("foir_assessment", {})
            foir_zone = foir_assess.get("foir_zone") or ob_metrics.get("foir_zone") or val_rep.get("foir_zone", "N/A")
            foir_thresh = foir_assess.get("applicable_threshold") or ob_metrics.get("applicable_foir_threshold", 50.0)
            max_elig_emi = foir_assess.get("max_eligible_emi") or ob_metrics.get("max_eligible_emi", 0.0)
            zone_emoji = {"SAFE": "🟢", "STRETCH": "🟡", "BREACH": "🟠", "CRITICAL": "🔴"}.get(foir_zone, "⚪")
            st.metric(label="FOIR (Fixed Obligation to Income Ratio)", value=f"{dti_val:.1f}%", delta=f"{zone_emoji} {foir_zone} Zone", delta_color="inverse" if dti_val > foir_thresh else "normal")
            existing_e = ob_metrics.get('total_existing_emis') or val_rep.get('total_existing_emis', 0.0)
            prop_e = ob_metrics.get('proposed_emi') or val_rep.get('proposed_emi', 0.0)
            st.caption(f"Slab Threshold: {foir_thresh:.0f}% | Max Eligible EMI: ₹{max_elig_emi:,.0f}")
            st.caption(f"Existing EMI: ₹{existing_e:,.0f} | Proposed: ₹{prop_e:,.0f}")

        with m3:
            st.metric(label="Income Variance", value=f"{inc_variance:.1f}%", delta="Clean Match" if inc_variance == 0 else f"{inc_variance:.1f}% gap", delta_color="off" if inc_variance <= 5 else "inverse")
            ver_net = inc_metrics.get('effective_verified_income') or val_rep.get('verified_monthly_net', 0.0)
            st.caption(f"Verified Net: ₹{ver_net:,.0f}/mo")
            
        with m4:
            st.metric(label="Credit Risk Score", value=f"{int(risk_score)}/100", delta=f"{routing_color} Tier")
            st.caption("Policy standard baseline: 100 pts")

        # Statement Balance Tamper Callout
        if stmt_stat == "MATCH":
            st.success("✅ **Bank Statement Arithmetic Reconciled:** Opening Balance + Total Credits − Total Debits == Stated Closing Balance.")
        elif stmt_stat == "MISMATCH":
            st.error(f"🚨 **Potential Statement Alteration / Tampering Detected:** Mathematical discrepancy of ₹{stmt_diff:,.2f} between calculated balance and closing balance.")

        # Executive Rationale & Reasons
        if underwriting.get("executive_rationale"):
            st.info(f"💡 **Executive Underwriting Rationale:** {underwriting.get('executive_rationale')}")
        if underwriting.get("conditions"):
            st.warning("⚠️ **Approval Conditions:**\n" + "\n".join([f"- {c}" for c in underwriting["conditions"]]))
        if underwriting.get("adverse_action_reasons"):
            st.error("❌ **Adverse Action Disqualification Reasons:**\n" + "\n".join([f"- {r}" for r in underwriting["adverse_action_reasons"]]))

        # --- Detailed Inspection Tabs ---
        tab_reconcile, tab_factors, tab_checklist, tab_docs = st.tabs([
            "📊 Step 4: Identity & Data Reconciliation",
            "🔍 Step 5 & 6: Math & Scoring Breakdown",
            "📋 Underwriter Sign-off Checklist",
            "📑 Raw Document Extractor & HITL Editor"
        ])

        with tab_reconcile:
            st.subheader("Cross-Document Field Matching Matrix")
            comparisons = step4_comp.get("comparisons") or val_rep.get("discrepancies") or []
            if comparisons:
                rows = []
                for c in comparisons:
                    rows.append({
                        "Field Inspected": c.get("field"),
                        "Declared (App Form)": str(c.get("declared_value") or "N/A"),
                        "Verified (Proofs)": str(c.get("verified_value") or "N/A"),
                        "Match Status": c.get("status"),
                        "Method": c.get("comparison_method"),
                        "Audit Rationale": c.get("reason")
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("No cross-document discrepancy items recorded.")

        with tab_factors:
            st.subheader("100-Point Deterministic Risk Ledger")
            factors = step6_risk.get("factor_breakdown") or val_rep.get("factor_breakdown") or {}
            if factors:
                f1, f2, f3, f4, f5 = st.columns(5)
                f1.metric("Base Score", f"{factors.get('base_score', 100):.0f}")
                f2.metric("Major Deductions", f"{factors.get('major_anomalies_deduction', 0):.0f} pts")
                f3.metric("Moderate Deductions", f"{factors.get('moderate_anomalies_deduction', 0):.0f} pts")
                f4.metric("Arithmetic Penalty", f"{factors.get('statement_arithmetic_deduction', 0):.0f} pts")
                foir_ded = factors.get('foir_zone_deduction', 0)
                foir_sev = factors.get('foir_breach_severity', 'none')
                f5.metric("FOIR Zone Penalty", f"{foir_ded:.0f} pts", delta=f"{foir_sev}" if foir_sev != "none" else None)

            cf_note = step6_risk.get("counterfactual_note") or val_rep.get("counterfactual_note")
            if cf_note:
                st.info(f"🧭 **Counterfactual Guidance:** {cf_note}")

            # Anomalies
            anomalies = step6_risk.get("anomalies") or val_rep.get("anomalies") or []
            if anomalies:
                st.markdown("##### 🚨 Policy Anomalies Identified")
                for anom in anomalies:
                    st.warning(f"**[{anom.get('code')}]** ({anom.get('severity')} Severity): {anom.get('description')}")
            else:
                st.success("✅ Zero critical policy anomalies detected.")

        with tab_checklist:
            st.subheader("Mandatory Compliance Checklist")
            checklist = step6_risk.get("reviewer_checklist") or val_rep.get("reviewer_checklist") or []
            if checklist:
                for idx, item in enumerate(checklist):
                    st.checkbox(item, key=f"chk_step_{app_id}_{idx}")
            else:
                st.checkbox("Confirm identity match across all submitted KYC proofs", key=f"chk_1_{app_id}")
                st.checkbox("Verify zero undisclosed loans in banking ledger", key=f"chk_2_{app_id}")
                st.checkbox("Sign off on final disbursement", key=f"chk_3_{app_id}")

        with tab_docs:
            st.subheader("Extracted Documents & Human-In-The-Loop Editor")
            docs = results.get("extracted_documents", [])
            for i, doc in enumerate(docs):
                fname = doc.get("filename")
                dtype = doc.get("document_type") or doc.get("doc_type", "UNKNOWN")
                conf = float(doc.get("confidence", 1.0)) * 100
                extracted = doc.get("extracted_data") or doc.get("extracted", {})

                with st.expander(f"📄 **{dtype}** — `{fname}` (Confidence: {conf:.1f}%)"):
                    with st.form(key=f"hitl_form_{i}_{app_id}"):
                        st.markdown("##### Edit & Verify OCR Values")
                        edited_fields = {}
                        cols = st.columns(2)
                        for idx, (k, v) in enumerate(extracted.items()):
                            col = cols[idx % 2]
                            edited_fields[k] = col.text_input(
                                label=k.replace("_", " ").title(),
                                value=str(v) if v is not None else "",
                                key=f"inp_{app_id}_{i}_{k}"
                            )

                        if st.form_submit_button("💾 Save Verified Field Data"):
                            save_payload = {
                                "application_id": app_id,
                                "filename": fname,
                                "original_extracted_data": extracted,
                                "verified_data": edited_fields
                            }
                            try:
                                s_res = requests.post(f"{API_BASE_URL}/api/save-verified-document/", json=save_payload)
                                if s_res.status_code == 200:
                                    st.success(f"Verified edits for `{fname}` committed to MongoDB audit logs!")
                                else:
                                    st.error(f"Failed to persist: {s_res.text}")
                            except Exception as err:
                                st.error(f"Save error: {err}")

# ==========================================
# PAGE 2: AUDIT & HISTORICAL ANALYTICS
# ==========================================
elif nav_selection == "Audit & Analytics":
    st.title("📊 Compliance Audit & Database Records")
    st.caption("Inspect live MongoDB Atlas collections for regulatory traceability and decision audit logs.")

    search_id = st.text_input("Enter Application ID (e.g., APP-xxxx):")
    if search_id and st.button("🔍 Fetch Record"):
        try:
            lookup = requests.get(f"{API_BASE_URL}/applications/{search_id.strip()}")
            if lookup.status_code == 200:
                record = lookup.json()
                st.success(f"✅ Record Found for `{search_id}`")
                st.json(record)
            else:
                st.error(f"Application ID `{search_id}` not found.")
        except requests.exceptions.ConnectionError:
            st.error("🚫 Backend unreachable.")