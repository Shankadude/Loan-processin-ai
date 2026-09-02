from typing import Any, Dict, List, Optional
from src.schemas.decision_models import Evidence, FieldComparison
from src.utils.normalizer import normalize_name, normalize_text, normalize_pan, normalize_dob, to_float


def compare_identity(
    declared: Dict[str, Any],
    verified: Dict[str, Any],
    all_docs: Optional[List[Dict[str, Any]]] = None
) -> List[FieldComparison]:
    results = []

    primary_kyc_name = verified.get("name")
    norm_kyc_name = normalize_name(primary_kyc_name)
    seen_checks = set()

    # 1. Cross-Document Verification vs Primary KYC
    if all_docs and norm_kyc_name:
        for doc in all_docs:
            doc_type = (doc.get("document_type") or doc.get("doc_type") or "UNKNOWN").upper()
            if doc_type in ["PAN_CARD", "IDENTITY_PROOF", "AADHAAR_CARD"]:
                continue

            extracted = doc.get("extracted_data") or doc.get("extracted", {})
            doc_name = (
                extracted.get("employee_name")
                or extracted.get("account_holder_name")
                or extracted.get("taxpayer_name")
            )

            check_key = f"{doc_type}_{doc_name}"
            if doc_name and check_key not in seen_checks:
                seen_checks.add(check_key)
                norm_doc_name = normalize_name(doc_name)

                if norm_doc_name == norm_kyc_name:
                    status = "MATCH"
                elif norm_doc_name in norm_kyc_name or norm_kyc_name in norm_doc_name:
                    status = "PARTIAL_MATCH"
                else:
                    status = "MISMATCH"

                results.append(
                    FieldComparison(
                        field=f"identity_check_{doc_type.lower()}",
                        declared_value=primary_kyc_name,
                        verified_value=doc_name,
                        normalized_declared=norm_kyc_name,
                        normalized_verified=norm_doc_name,
                        status=status,
                        comparison_method="DETERMINISTIC",
                        evidence=[
                            Evidence(
                                source_document="PRIMARY_KYC",
                                source_path="name",
                                field="name",
                                value=primary_kyc_name,
                                evidence_type="VERIFIED",
                            ),
                            Evidence(
                                source_document=doc_type,
                                source_path="employee_name/account_holder_name",
                                field="name",
                                value=doc_name,
                                evidence_type="VERIFIED",
                            ),
                        ],
                        reason=f"Cross-document validation: Primary KYC ('{norm_kyc_name}') vs {doc_type} ('{norm_doc_name}').",
                    )
                )

    # 2. Declared vs KYC Check
    declared_name = declared.get("name")
    d_name = normalize_name(declared_name)

    if not d_name or not norm_kyc_name:
        name_status = "NOT_AVAILABLE"
    elif d_name == norm_kyc_name:
        name_status = "MATCH"
    elif d_name in norm_kyc_name or norm_kyc_name in d_name:
        name_status = "PARTIAL_MATCH"
    else:
        name_status = "MISMATCH"

    results.append(
        FieldComparison(
            field="declared_vs_kyc_name",
            declared_value=declared_name,
            verified_value=primary_kyc_name,
            normalized_declared=d_name,
            normalized_verified=norm_kyc_name,
            status=name_status,
            comparison_method="DETERMINISTIC",
            evidence=[],
            reason=f"Declared name '{d_name}' vs KYC record '{norm_kyc_name}'.",
        )
    )

    # 3. DOB Check
    declared_dob = normalize_dob(declared.get("dob"))
    verified_dob = normalize_dob(verified.get("dob"))

    if not declared_dob or not verified_dob:
        dob_status = "NOT_AVAILABLE"
    elif declared_dob == verified_dob:
        dob_status = "MATCH"
    else:
        dob_status = "MISMATCH"

    results.append(
        FieldComparison(
            field="dob",
            declared_value=declared.get("dob"),
            verified_value=verified.get("dob"),
            normalized_declared=declared_dob,
            normalized_verified=verified_dob,
            status=dob_status,
            comparison_method="DETERMINISTIC",
            evidence=[],
            reason="Exact DOB comparison.",
        )
    )

    return results


def compare_income(declared: Dict[str, Any], verified: Dict[str, Any]) -> FieldComparison:
    declared_income = to_float(declared.get("net_monthly"))
    verified_income = to_float(verified.get("payslip_net_monthly"))
    difference = abs(declared_income - verified_income)

    if declared_income == 0 or verified_income == 0:
        status = "NOT_AVAILABLE"
        percentage = None
    else:
        percentage = round((difference / declared_income) * 100, 2)
        if percentage <= 5:
            status = "MATCH"
        elif percentage <= 10:
            status = "PARTIAL_MATCH"
        else:
            status = "MISMATCH"

    return FieldComparison(
        field="net_monthly_income",
        declared_value=declared_income,
        verified_value=verified_income,
        normalized_declared=declared_income,
        normalized_verified=verified_income,
        status=status,
        discrepancy_amount=round(difference, 2),
        discrepancy_percent=percentage,
        comparison_method="DETERMINISTIC",
        evidence=[],
        reason=f"Difference = Rs. {difference:.2f}, variance = {percentage}%.",
    )


def compare_employer(declared: Dict[str, Any], verified: Dict[str, Any]) -> FieldComparison:
    declared_employer = normalize_text(declared.get("employer"))
    verified_employer = normalize_text(verified.get("employer"))

    if not declared_employer or not verified_employer:
        status = "NOT_AVAILABLE"
    elif declared_employer == verified_employer:
        status = "MATCH"
    elif declared_employer in verified_employer or verified_employer in declared_employer:
        status = "PARTIAL_MATCH"
    else:
        status = "MISMATCH"

    return FieldComparison(
        field="employer",
        declared_value=declared.get("employer"),
        verified_value=verified.get("employer"),
        normalized_declared=declared_employer,
        normalized_verified=verified_employer,
        status=status,
        comparison_method="DETERMINISTIC",
        evidence=[],
        reason="Normalized employer comparison.",
    )


def compare_pan(declared: Dict[str, Any], verified: Dict[str, Any]) -> FieldComparison:
    declared_pan = normalize_pan(declared.get("pan_number") or declared.get("pan"))
    verified_pan = normalize_pan(verified.get("pan_number"))

    if not declared_pan or not verified_pan:
        status = "NOT_AVAILABLE"
    elif declared_pan == verified_pan:
        status = "MATCH"
    else:
        status = "MISMATCH"

    return FieldComparison(
        field="pan_number",
        declared_value=declared_pan,
        verified_value=verified_pan,
        normalized_declared=declared_pan,
        normalized_verified=verified_pan,
        status=status,
        comparison_method="DETERMINISTIC",
        evidence=[],
        reason=f"PAN match check: Declared '{declared_pan}' vs Verified '{verified_pan}'.",
    )