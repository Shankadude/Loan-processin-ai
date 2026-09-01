import json
import os
from pathlib import Path


def load_policy(policy_name: str = "personal_loan") -> dict:
    """
    Loads lender underwriting policy rules dynamically from the policies/ directory.
    """
    current_dir = Path(__file__).parent
    policy_file = current_dir / f"{policy_name}_rules.json"

    if not policy_file.exists():
        # Fallback to standard personal loan rules
        policy_file = current_dir / "personal_loan_rules.json"

    if policy_file.exists():
        with open(policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("rules", {})

    # Safe default fallback
    return {
        "foir": {"standard_threshold_percent": 50.0, "max_acceptable_percent": 60.0},
        "income": {"min_monthly_net_income": 25000.0, "max_acceptable_variance_percent": 10.0},
        "liabilities": {"max_allowed_undisclosed_emi_gap": 2000.0},
        "statement": {"require_arithmetic_balance_match": true, "max_balance_reconciliation_error": 5.0},
        "scoring_weights": {
            "base_score": 100.0,
            "minor_anomaly_deduction": 10.0,
            "moderate_anomaly_deduction": 25.0,
            "major_anomaly_deduction": 45.0,
            "arithmetic_mismatch_deduction": 30.0,
            "eligibility_failure_deduction": 50.0,
        },
        "routing_thresholds": {"green_min_score": 80.0, "amber_min_score": 50.0},
    }
