"""
Performance Tests: Latency and Load
Tests execution time of deterministic pipeline stages and simulates concurrent load.
These tests measure performance of pure computation - NO LLM calls.

Run:  python -m pytest tests/performance/test_latency_and_load.py -v
"""
import time
import asyncio
import pytest
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.decision_engine.extractors import extract_declared, extract_verified, extract_liabilities
from src.decision_engine.comparison import compare_identity, compare_income, compare_employer, compare_pan
from src.decision_engine.risk_scorer import score_application
from src.decision_engine.calculations import (
    calculate_income_metrics,
    calculate_obligation_metrics,
    validate_statement_arithmetic,
    check_eligibility,
)
from src.decision_engine.discrepancy import detect_discrepancies
from src.utils.assembly import find_missing_documents
from src.utils.normalizer import normalize_name, normalize_text, normalize_pan


pytestmark = pytest.mark.performance

GOLDEN_DATA_PATH = Path(__file__).parent.parent / "golden_data" / "sample_documents_with_expected_outputs.json"


@pytest.fixture(scope="module")
def all_scenarios():
    with open(GOLDEN_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]


def _run_full_scoring(scenario):
    """Run the full deterministic scoring pipeline for a scenario."""
    declared = scenario["declared"]
    documents = scenario["documents"]
    payload = {"documents": documents}

    extracted_declared = extract_declared(payload)
    extracted_verified = extract_verified(payload)
    extracted_liabilities = extract_liabilities(payload)

    for key in ["name", "dob", "pan_number", "employer", "net_monthly", "gross_monthly"]:
        if declared.get(key) is not None:
            extracted_declared[key] = declared[key]

    verified = scenario.get("verified", {})
    for key in ["name", "dob", "pan_number", "employer", "payslip_net_monthly", "bank_avg_salary_credit"]:
        if verified.get(key) is not None:
            extracted_verified[key] = verified[key]

    liabilities = scenario.get("liabilities", extracted_liabilities)

    comparisons = compare_identity(extracted_declared, extracted_verified, all_docs=documents)
    comparisons.append(compare_pan(extracted_declared, extracted_verified))
    comparisons.append(compare_income(extracted_declared, extracted_verified))
    comparisons.append(compare_employer(extracted_declared, extracted_verified))

    bank_data = scenario.get("bank_statement", {})

    result = score_application(
        application_id="PERF-TEST",
        declared_payload=extracted_declared,
        verified_payload=extracted_verified,
        liabilities_payload=liabilities,
        comparisons=comparisons,
        bank_statement_data=bank_data if bank_data else None,
        requested_amount=float(declared.get("loan_amount_requested", 0)),
    )
    return result


# ==========================================================================
# 1. Individual Stage Latency Tests
# ==========================================================================

class TestStageLantecy:
    """Tests that individual computation stages complete within acceptable time."""

    def test_normalizer_speed(self):
        """Normalizer functions should handle 10,000 iterations under 1 second."""
        start = time.perf_counter()
        for _ in range(10000):
            normalize_name("Dr. Avinash Kumar-Bhatt (Mr.)")
            normalize_text("Infosys Limited Pvt. Ltd.")
            normalize_pan("avi bh 2505 f")
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Normalizer took {elapsed:.3f}s for 10,000 iterations"

    def test_income_metrics_speed(self):
        """Income metrics calculation: 1000 iterations under 0.5s."""
        start = time.perf_counter()
        for _ in range(1000):
            calculate_income_metrics(
                declared_net=72000.0,
                verified_net=70000.0,
                bank_avg_credit=69000.0,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Income metrics took {elapsed:.3f}s for 1000 iterations"

    def test_obligation_metrics_speed(self):
        """Obligation metrics calculation: 1000 iterations under 0.5s."""
        start = time.perf_counter()
        for _ in range(1000):
            calculate_obligation_metrics(
                detected_emi=15000.0,
                declared_liabilities=[
                    {"emi_amount": 8000.0},
                    {"emi_amount": 5000.0},
                ],
                verified_monthly_net=72000.0,
                proposed_emi=7500.0,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Obligation metrics took {elapsed:.3f}s for 1000 iterations"

    def test_statement_arithmetic_speed(self):
        """Statement validation: 1000 iterations under 0.5s."""
        start = time.perf_counter()
        for _ in range(1000):
            validate_statement_arithmetic(
                opening_balance=125000.0,
                total_credits=215000.0,
                total_debits=180000.0,
                closing_balance=160000.0,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Statement arithmetic took {elapsed:.3f}s for 1000 iterations"

    def test_eligibility_check_speed(self):
        """Eligibility check: 1000 iterations under 0.5s."""
        start = time.perf_counter()
        for _ in range(1000):
            check_eligibility(
                verified_income=72000.0,
                foir_percentage=35.0,
                income_variance_percent=5.0,
                undisclosed_liability_gap=1000.0,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Eligibility check took {elapsed:.3f}s for 1000 iterations"

    def test_missing_documents_speed(self):
        """Missing document check: 1000 iterations under 0.5s."""
        docs = [
            {"doc_type": "PAYSLIP"},
            {"doc_type": "BANK_STATEMENT"},
            {"doc_type": "PAN_CARD"},
            {"doc_type": "LOAN_APPLICATION"},
        ]
        start = time.perf_counter()
        for _ in range(1000):
            find_missing_documents(docs)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Missing docs check took {elapsed:.3f}s for 1000 iterations"


# ==========================================================================
# 2. Full Pipeline Latency Tests
# ==========================================================================

class TestPipelineLatency:
    """Tests full deterministic pipeline execution time."""

    def test_single_clean_scenario_under_500ms(self, all_scenarios):
        scenario = all_scenarios["clean_approval"]
        start = time.perf_counter()
        result = _run_full_scoring(scenario)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Clean scenario took {elapsed:.3f}s"
        assert result is not None

    def test_single_fraud_scenario_under_500ms(self, all_scenarios):
        scenario = all_scenarios["identity_fraud_reject"]
        start = time.perf_counter()
        result = _run_full_scoring(scenario)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Fraud scenario took {elapsed:.3f}s"
        assert result is not None

    def test_all_scenarios_under_2s(self, all_scenarios):
        """All 6 scenarios sequentially should complete under 2 seconds."""
        start = time.perf_counter()
        for name, scenario in all_scenarios.items():
            if "verified" in scenario:
                _run_full_scoring(scenario)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"All scenarios took {elapsed:.3f}s"


# ==========================================================================
# 3. Concurrent Load Tests
# ==========================================================================

class TestConcurrentLoad:
    """Tests pipeline under simulated concurrent load."""

    def test_10_concurrent_applications(self, all_scenarios):
        """Simulates 10 concurrent applications processed in parallel."""
        scenario = all_scenarios["clean_approval"]

        def run_one(_):
            return _run_full_scoring(scenario)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(run_one, range(10)))
        elapsed = time.perf_counter() - start

        assert len(results) == 10
        assert all(r is not None for r in results)
        assert elapsed < 5.0, f"10 concurrent apps took {elapsed:.3f}s"

    def test_50_sequential_applications(self, all_scenarios):
        """50 sequential pipeline executions should complete under 10 seconds."""
        scenario = all_scenarios["clean_approval"]
        start = time.perf_counter()
        for _ in range(50):
            _run_full_scoring(scenario)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"50 sequential apps took {elapsed:.3f}s"

    def test_mixed_scenarios_concurrent(self, all_scenarios):
        """Runs a mix of different scenarios concurrently."""
        scenarios_with_verified = [
            s for s in all_scenarios.values() if "verified" in s
        ]

        def run_scenario(scenario):
            return _run_full_scoring(scenario)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(run_scenario, scenarios_with_verified * 3))
        elapsed = time.perf_counter() - start

        assert all(r is not None for r in results)
        assert elapsed < 5.0, f"Mixed concurrent took {elapsed:.3f}s"


# ==========================================================================
# 4. Comparison Engine Load Tests
# ==========================================================================

class TestComparisonLoad:
    """Tests comparison functions under heavy iteration."""

    def test_identity_comparison_1000x(self, all_scenarios):
        scenario = all_scenarios["clean_approval"]
        declared = scenario["declared"]
        verified = scenario["verified"]
        docs = scenario["documents"]

        start = time.perf_counter()
        for _ in range(1000):
            compare_identity(declared, verified, all_docs=docs)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"1000 identity comparisons took {elapsed:.3f}s"

    def test_full_comparison_suite_1000x(self, all_scenarios):
        scenario = all_scenarios["clean_approval"]
        declared = scenario["declared"]
        verified = scenario["verified"]

        start = time.perf_counter()
        for _ in range(1000):
            compare_identity(declared, verified)
            compare_pan(declared, verified)
            compare_income(declared, verified)
            compare_employer(declared, verified)
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, f"1000 full comparison suites took {elapsed:.3f}s"
