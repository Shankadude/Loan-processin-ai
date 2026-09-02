"""
API Tests: FastAPI Endpoint Contract Tests
Tests the FastAPI application endpoints for correct HTTP contracts,
request/response shapes, status codes, and error handling.
Uses httpx AsyncClient with the FastAPI test client (no real server needed).
Mocks the pipeline and MongoDB to test API layer in isolation.

Run:  python -m pytest tests/api/test_fastapi_endpoints.py -v
"""
import io
import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport
from api import app


pytestmark = pytest.mark.api


@pytest.fixture
def mock_pipeline_result():
    """Returns a representative pipeline result dict."""
    return {
        "application_id": "APP-test1234",
        "status": "EXTRACTED",
        "missing_documents": [],
        "declared_monthly_income": 72000.0,
        "requested_loan_amount": 300000.0,
        "extracted_documents": [
            {"filename": "payslip.pdf", "doc_type": "PAYSLIP", "confidence": 0.92, "extracted": {}},
            {"filename": "pan.pdf", "doc_type": "PAN_CARD", "confidence": 0.96, "extracted": {}},
            {"filename": "bank.pdf", "doc_type": "BANK_STATEMENT", "confidence": 0.90, "extracted": {}},
        ],
        "validation_report": {
            "routing_color": "GREEN",
            "recommendation": "AUTO_APPROVE",
            "risk_score": 90,
            "step4_comparison": {},
            "step5_calculation": {},
            "step6_risk_anomaly": {},
        },
        "decision_result": {},
        "underwriting_decision": {
            "verdict": "APPROVED",
            "risk_score_summary": "Clean profile",
            "conditions": [],
            "adverse_action_reasons": [],
            "executive_rationale": "Low risk, auto-approved.",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==========================================================================
# 1. Health Check Endpoint
# ==========================================================================

class TestHealthCheck:
    """Tests GET / health check."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "service" in data


# ==========================================================================
# 2. Create Application Endpoint (POST /applications)
# ==========================================================================

class TestCreateApplication:
    """Tests POST /applications endpoint contract."""

    @pytest.mark.asyncio
    async def test_no_files_returns_400(self):
        """Should return 400 when no files are uploaded (FastAPI validation)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/applications",
                data={"declared_income": 72000.0, "requested_amount": 300000.0},
                # No files parameter
            )
        assert response.status_code == 422  # FastAPI validation error (missing required 'files')

    @pytest.mark.asyncio
    async def test_successful_application(self, mock_pipeline_result):
        """Tests that a valid request returns 200 with expected shape."""
        with patch("api.execute_loan_workflow", new_callable=AsyncMock) as mock_workflow, \
             patch("api.applications_collection") as mock_apps, \
             patch("api.comparison_results_collection") as mock_comp, \
             patch("api.step5_and_6_collection") as mock_s56, \
             patch("api.full_pipeline_collection") as mock_full:

            mock_workflow.return_value = mock_pipeline_result
            mock_apps.insert_one = AsyncMock()
            mock_comp.update_one = AsyncMock()
            mock_s56.update_one = AsyncMock()
            mock_full.update_one = AsyncMock()

            # Create a fake file
            fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
            fake_pdf.name = "test_payslip.pdf"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/applications",
                    data={"declared_income": "72000.0", "requested_amount": "300000.0"},
                    files=[("files", ("test_payslip.pdf", fake_pdf, "application/pdf"))],
                )

            assert response.status_code == 200
            data = response.json()
            assert "application_id" in data
            assert "status" in data
            assert "extracted_documents" in data

    @pytest.mark.asyncio
    async def test_pipeline_error_returns_500(self):
        """Tests that pipeline errors return 500."""
        with patch("api.execute_loan_workflow", new_callable=AsyncMock) as mock_workflow:
            mock_workflow.side_effect = RuntimeError("Pipeline exploded")

            fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/applications",
                    data={"declared_income": "72000.0", "requested_amount": "300000.0"},
                    files=[("files", ("test.pdf", fake_pdf, "application/pdf"))],
                )

            assert response.status_code == 500
            assert "Pipeline error" in response.json()["detail"]


# ==========================================================================
# 3. Get Application Details Endpoint (GET /applications/{id})
# ==========================================================================

class TestGetApplicationDetails:
    """Tests GET /applications/{application_id} endpoint."""

    @pytest.mark.asyncio
    async def test_existing_application(self, mock_pipeline_result):
        app_id = "APP-test1234"
        with patch("api.applications_collection") as mock_coll:
            mock_coll.find_one = AsyncMock(return_value=mock_pipeline_result)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/applications/{app_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["application_id"] == app_id

    @pytest.mark.asyncio
    async def test_nonexistent_application_returns_404(self):
        with patch("api.applications_collection") as mock_coll:
            mock_coll.find_one = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/applications/NONEXISTENT-ID")

            assert response.status_code == 404


# ==========================================================================
# 4. Add More Documents Endpoint (POST /applications/{id}/documents)
# ==========================================================================

class TestAddMoreDocuments:
    """Tests POST /applications/{id}/documents endpoint."""

    @pytest.mark.asyncio
    async def test_add_to_nonexistent_returns_404(self):
        with patch("api.applications_collection") as mock_coll:
            mock_coll.find_one = AsyncMock(return_value=None)

            fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/applications/NONEXISTENT-ID/documents",
                    files=[("files", ("extra.pdf", fake_pdf, "application/pdf"))],
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_documents_success(self, mock_pipeline_result):
        existing = {
            "application_id": "APP-exist123",
            "declared_monthly_income": 72000.0,
            "requested_loan_amount": 300000.0,
            "extracted_documents": [],
        }

        with patch("api.applications_collection") as mock_coll, \
             patch("api.execute_loan_workflow", new_callable=AsyncMock) as mock_workflow, \
             patch("api.comparison_results_collection") as mock_comp, \
             patch("api.step5_and_6_collection") as mock_s56, \
             patch("api.full_pipeline_collection") as mock_full:

            mock_coll.find_one = AsyncMock(side_effect=[existing, mock_pipeline_result])
            mock_coll.update_one = AsyncMock()
            mock_workflow.return_value = mock_pipeline_result
            mock_comp.update_one = AsyncMock()
            mock_s56.update_one = AsyncMock()
            mock_full.update_one = AsyncMock()

            fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/applications/APP-exist123/documents",
                    files=[("files", ("extra.pdf", fake_pdf, "application/pdf"))],
                )

            assert response.status_code == 200


# ==========================================================================
# 5. Human Override Endpoint (POST /api/save-verified-document/)
# ==========================================================================

class TestSaveVerifiedDocument:
    """Tests POST /api/save-verified-document/ endpoint."""

    @pytest.mark.asyncio
    async def test_save_verified_success(self):
        with patch("api.verified_collection") as mock_coll:
            mock_coll.update_many = AsyncMock()
            mock_insert = AsyncMock()
            mock_insert.return_value = MagicMock(inserted_id="abc123")
            mock_coll.insert_one = mock_insert

            payload = {
                "application_id": "APP-test1234",
                "filename": "payslip.pdf",
                "original_extracted_data": {"net_pay": 72000.0},
                "verified_data": {"net_pay": 73000.0},
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/save-verified-document/",
                    json=payload,
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "id" in data

    @pytest.mark.asyncio
    async def test_save_verified_missing_fields_returns_422(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/save-verified-document/",
                json={"application_id": "APP-test1234"},  # Missing required fields
            )
        assert response.status_code == 422


# ==========================================================================
# 6. Alternative Route Tests
# ==========================================================================

class TestAlternativeRoutes:
    """Tests that dual-path routes work (e.g., /api/process-loan-application/)."""

    @pytest.mark.asyncio
    async def test_alt_route_no_files_returns_422(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/process-loan-application/",
                data={"declared_income": "72000.0", "requested_amount": "300000.0"},
            )
        assert response.status_code == 422
