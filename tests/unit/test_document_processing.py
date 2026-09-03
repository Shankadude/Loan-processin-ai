"""
Unit Tests: Document Processing (OCR / Parsing / Validation)
Tests the normalizer utilities, document assembly helpers, and PDF utilities.
These tests do NOT call any LLM/Vision APIs - they test pure deterministic logic only.

Run:  python -m pytest tests/unit/test_document_processing.py -v
"""
import pytest
from src.utils.normalizer import normalize_name, normalize_text, normalize_pan, normalize_dob, to_float
from src.utils.assembly import find_missing_documents, build_applicant_block, REQUIRED_DOCUMENT_TYPES
from src.schemas.document_models import (
    PanCardData, AadhaarCardData, PayslipData, BankStatementData,
    Form16Data, LoanApplicationData, ExtractedDocuments, Transaction,
)


# ==========================================================================
# 1. Normalizer Tests
# ==========================================================================

class TestNormalizeName:
    """Tests for normalize_name: uppercases, removes special chars, collapses whitespace."""

    def test_basic_name(self):
        assert normalize_name("Avinash Bhatt") == "AVINASH BHATT"

    def test_name_with_special_chars(self):
        assert normalize_name("Dr. Priya-Sharma (Ms.)") == "DR PRIYA SHARMA MS"

    def test_name_with_extra_whitespace(self):
        assert normalize_name("  Rajesh   Kumar  ") == "RAJESH KUMAR"

    def test_none_returns_empty(self):
        assert normalize_name(None) == ""

    def test_numeric_in_name(self):
        assert normalize_name("Room 42 Suite") == "ROOM 42 SUITE"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_already_uppercase(self):
        assert normalize_name("SANJAY GUPTA") == "SANJAY GUPTA"


class TestNormalizeText:
    """Tests for normalize_text: lowercases, removes special chars."""

    def test_basic_text(self):
        assert normalize_text("Infosys Ltd.") == "infosys ltd"

    def test_text_with_symbols(self):
        assert normalize_text("TCS (India) Pvt. Ltd.") == "tcs india pvt ltd"

    def test_none_returns_empty(self):
        assert normalize_text(None) == ""

    def test_preserves_numbers(self):
        assert normalize_text("Floor 5, Building 12") == "floor 5 building 12"


class TestNormalizePan:
    """Tests for normalize_pan: uppercases and strips spaces."""

    def test_basic_pan(self):
        assert normalize_pan("avibh2505f") == "AVIBH2505F"

    def test_pan_with_spaces(self):
        assert normalize_pan("AVI BH 2505 F") == "AVIBH2505F"

    def test_none_returns_empty(self):
        assert normalize_pan(None) == ""


class TestNormalizeDob:
    """Tests for normalize_dob: strips whitespace."""

    def test_basic_dob(self):
        assert normalize_dob("25/05/1990") == "25/05/1990"

    def test_dob_with_whitespace(self):
        assert normalize_dob("  25/05/1990  ") == "25/05/1990"

    def test_none_returns_empty(self):
        assert normalize_dob(None) == ""


class TestToFloat:
    """Tests for to_float: safe numeric conversion."""

    def test_integer_string(self):
        assert to_float("72000") == 72000.0

    def test_float_string(self):
        assert to_float("72000.50") == 72000.50

    def test_none(self):
        assert to_float(None) == 0.0

    def test_empty_string(self):
        assert to_float("") == 0.0

    def test_invalid_string(self):
        assert to_float("not_a_number") == 0.0

    def test_actual_float(self):
        assert to_float(55000.0) == 55000.0

    def test_actual_int(self):
        assert to_float(55000) == 55000.0


# ==========================================================================
# 2. Document Assembly / Missing Document Detection
# ==========================================================================

class TestFindMissingDocuments:
    """Tests for find_missing_documents: detects which required doc types are absent."""

    def test_all_present(self):
        docs = [
            {"doc_type": "PAYSLIP"},
            {"doc_type": "BANK_STATEMENT"},
            {"doc_type": "PAN_CARD"},
            {"doc_type": "LOAN_APPLICATION"},
        ]
        missing = find_missing_documents(docs)
        assert missing == []

    def test_missing_payslip(self):
        docs = [
            {"doc_type": "BANK_STATEMENT"},
            {"doc_type": "PAN_CARD"},
        ]
        missing = find_missing_documents(docs)
        assert "PAYSLIP" in missing

    def test_missing_all_required(self):
        docs = [{"doc_type": "LOAN_APPLICATION"}]
        missing = find_missing_documents(docs)
        assert len(missing) == len(REQUIRED_DOCUMENT_TYPES)

    def test_empty_docs_list(self):
        missing = find_missing_documents([])
        assert len(missing) == len(REQUIRED_DOCUMENT_TYPES)

    def test_salary_slip_alias(self):
        """SALARY_SLIP should satisfy the PAYSLIP requirement."""
        docs = [
            {"doc_type": "SALARY_SLIP"},
            {"doc_type": "BANK_STATEMENT"},
            {"doc_type": "PAN_CARD"},
        ]
        missing = find_missing_documents(docs)
        assert "PAYSLIP" not in missing

    def test_pan_alias(self):
        """PAN should satisfy PAN_CARD requirement."""
        docs = [
            {"doc_type": "PAYSLIP"},
            {"doc_type": "BANK_STATEMENT"},
            {"doc_type": "PAN"},
        ]
        missing = find_missing_documents(docs)
        assert "PAN_CARD" not in missing

    def test_uses_document_type_key(self):
        """Should also check 'document_type' key."""
        docs = [
            {"document_type": "PAYSLIP"},
            {"document_type": "BANK_STATEMENT"},
            {"document_type": "PAN_CARD"},
        ]
        missing = find_missing_documents(docs)
        assert missing == []


class TestBuildApplicantBlock:
    """Tests for build_applicant_block: constructs applicant identity from KYC docs."""

    def test_from_aadhaar(self):
        data = ExtractedDocuments(
            aadhaar_card=AadhaarCardData(full_name="AVINASH BHATT", dob="25/05/1990"),
            pan_card=PanCardData(full_name="AVINASH BHATT", pan_number="AVIBH2505F", dob="25/05/1990"),
        )
        result = build_applicant_block(data)
        assert result["full_name"] == "AVINASH BHATT"
        assert result["pan_number"] == "AVIBH2505F"
        assert result["dob"] == "25/05/1990"

    def test_from_pan_only(self):
        data = ExtractedDocuments(
            pan_card=PanCardData(full_name="PRIYA SHARMA", pan_number="PRISH1903F", dob="19/03/1988"),
        )
        result = build_applicant_block(data)
        assert result["full_name"] == "PRIYA SHARMA"
        assert result["pan_number"] == "PRISH1903F"

    def test_no_kyc_docs(self):
        data = ExtractedDocuments()
        result = build_applicant_block(data)
        assert result["full_name"] is None
        assert result["pan_number"] is None


# ==========================================================================
# 3. Pydantic Document Model Validation
# ==========================================================================

class TestDocumentModels:
    """Tests for Pydantic schema validation of document data models."""

    def test_payslip_model_valid(self):
        ps = PayslipData(
            employee_name="Avinash Bhatt",
            employer_name="Infosys Ltd",
            net_pay=72000.0,
            gross_earnings=85000.0,
            total_deductions=13000.0,
        )
        assert ps.employee_name == "Avinash Bhatt"
        assert ps.net_pay == 72000.0

    def test_bank_statement_model_valid(self):
        bs = BankStatementData(
            account_holder_name="Avinash Bhatt",
            bank_name="HDFC Bank",
            opening_balance=125000.0,
            closing_balance=160000.0,
            total_credits=215000.0,
            total_debits=180000.0,
            transactions=[
                Transaction(date="2025-03-01", narration="SAL INFOSYS", amount=71500.0, category="salary_credit"),
            ]
        )
        assert bs.account_holder_name == "Avinash Bhatt"
        assert len(bs.transactions) == 1
        assert bs.transactions[0].category == "salary_credit"

    def test_pan_card_model_valid(self):
        pan = PanCardData(full_name="AVINASH BHATT", pan_number="AVIBH2505F", dob="25/05/1990")
        assert pan.pan_number == "AVIBH2505F"

    def test_loan_application_model_defaults(self):
        la = LoanApplicationData(name="Test User", employer="TestCo")
        assert la.tenure_months == 12
        assert la.liabilities == []
        assert la.gross_monthly == 0.0

    def test_form16_model_valid(self):
        f16 = Form16Data(
            employee_name="Avinash Bhatt",
            pan_number="AVIBH2505F",
            employer_name="Infosys Ltd",
            annual_gross=1020000.0,
            annual_tds=45000.0,
        )
        assert f16.annual_gross == 1020000.0
