"""
Integration Tests: MongoDB Stage Persistence
Tests that each pipeline stage correctly writes/reads documents to MongoDB collections.
Requires a running MongoDB instance (local or Atlas, configured via .env).

Run:  python -m pytest tests/integration/test_stage_to_mongodb.py -v
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone

# Skip entire module if MongoDB is unavailable
try:
    from src.database.mongo import (
        applications_collection,
        verified_collection,
        comparison_results_collection,
        step5_and_6_collection,
        full_pipeline_collection,
    )
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not MONGO_AVAILABLE, reason="MongoDB not available"),
]


def _gen_app_id():
    return f"TEST-{str(uuid.uuid4())[:8]}"


@pytest.fixture
def app_id():
    return _gen_app_id()


# ==========================================================================
# 1. Applications Collection (Loan Applications)
# ==========================================================================

class TestApplicationsCollection:
    """Tests CRUD operations on the loan_applications collection."""

    @pytest.mark.asyncio
    async def test_insert_and_find(self, app_id):
        doc = {
            "application_id": app_id,
            "status": "EXTRACTED",
            "declared_monthly_income": 72000.0,
            "requested_loan_amount": 300000.0,
            "extracted_documents": [{"doc_type": "PAYSLIP", "filename": "payslip.pdf"}],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await applications_collection.insert_one(doc)
        found = await applications_collection.find_one({"application_id": app_id}, {"_id": 0})
        assert found is not None
        assert found["application_id"] == app_id
        assert found["status"] == "EXTRACTED"
        # Cleanup
        await applications_collection.delete_one({"application_id": app_id})

    @pytest.mark.asyncio
    async def test_update_status(self, app_id):
        doc = {"application_id": app_id, "status": "INCOMPLETE"}
        await applications_collection.insert_one(doc)

        await applications_collection.update_one(
            {"application_id": app_id},
            {"$set": {"status": "EXTRACTED", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        found = await applications_collection.find_one({"application_id": app_id})
        assert found["status"] == "EXTRACTED"
        # Cleanup
        await applications_collection.delete_one({"application_id": app_id})

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        found = await applications_collection.find_one({"application_id": "NONEXISTENT-ID"})
        assert found is None


# ==========================================================================
# 2. Verified Documents Collection
# ==========================================================================

class TestVerifiedCollection:
    """Tests for human-verified document storage."""

    @pytest.mark.asyncio
    async def test_insert_verified_doc(self, app_id):
        record = {
            "application_id": app_id,
            "filename": "payslip.pdf",
            "original_extracted_data": {"net_pay": 72000.0},
            "verified_data": {"net_pay": 73000.0},
            "verified_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        result = await verified_collection.insert_one(record)
        assert result.inserted_id is not None

        found = await verified_collection.find_one({"application_id": app_id, "is_active": True})
        assert found is not None
        assert found["verified_data"]["net_pay"] == 73000.0
        # Cleanup
        await verified_collection.delete_many({"application_id": app_id})

    @pytest.mark.asyncio
    async def test_deactivate_previous_version(self, app_id):
        """Simulates the audit trail: old version deactivated, new version inserted."""
        old_record = {
            "application_id": app_id,
            "filename": "payslip.pdf",
            "is_active": True,
            "verified_data": {"net_pay": 72000.0},
        }
        await verified_collection.insert_one(old_record)

        # Deactivate old
        await verified_collection.update_many(
            {"application_id": app_id, "filename": "payslip.pdf", "is_active": True},
            {"$set": {"is_active": False}},
        )

        # Insert new version
        new_record = {
            "application_id": app_id,
            "filename": "payslip.pdf",
            "is_active": True,
            "verified_data": {"net_pay": 73000.0},
        }
        await verified_collection.insert_one(new_record)

        active = await verified_collection.find_one({"application_id": app_id, "is_active": True})
        assert active["verified_data"]["net_pay"] == 73000.0

        inactive_count = 0
        async for doc in verified_collection.find({"application_id": app_id, "is_active": False}):
            inactive_count += 1
        assert inactive_count >= 1
        # Cleanup
        await verified_collection.delete_many({"application_id": app_id})


# ==========================================================================
# 3. Comparison Results Collection (Step 4)
# ==========================================================================

class TestComparisonResultsCollection:
    """Tests Step 4 comparison results persistence."""

    @pytest.mark.asyncio
    async def test_upsert_comparison(self, app_id):
        step4_data = {
            "identity_status": "MATCH",
            "income_status": "MATCH",
            "overall_status": "MATCH",
            "comparisons": [{"field": "name", "status": "MATCH"}],
        }
        await comparison_results_collection.update_one(
            {"application_id": app_id},
            {"$set": {**step4_data, "application_id": app_id}},
            upsert=True,
        )
        found = await comparison_results_collection.find_one({"application_id": app_id})
        assert found is not None
        assert found["identity_status"] == "MATCH"
        # Cleanup
        await comparison_results_collection.delete_one({"application_id": app_id})

    @pytest.mark.asyncio
    async def test_upsert_overwrites(self, app_id):
        # First insert
        await comparison_results_collection.update_one(
            {"application_id": app_id},
            {"$set": {"application_id": app_id, "identity_status": "MATCH"}},
            upsert=True,
        )
        # Overwrite
        await comparison_results_collection.update_one(
            {"application_id": app_id},
            {"$set": {"identity_status": "MISMATCH"}},
            upsert=True,
        )
        found = await comparison_results_collection.find_one({"application_id": app_id})
        assert found["identity_status"] == "MISMATCH"
        # Cleanup
        await comparison_results_collection.delete_one({"application_id": app_id})


# ==========================================================================
# 4. Step 5 & 6 Collection (Financials + Risk)
# ==========================================================================

class TestStep5And6Collection:
    """Tests combined financial calculation and risk scoring persistence."""

    @pytest.mark.asyncio
    async def test_upsert_step5_and_6(self, app_id):
        data = {
            "application_id": app_id,
            "step5_calculation": {"income_metrics": {"effective_verified_income": 72000.0}},
            "step6_risk_anomaly": {"risk_score": 90, "routing_color": "GREEN"},
            "routing_color": "GREEN",
            "risk_score": 90,
            "recommendation": "AUTO_APPROVE",
        }
        await step5_and_6_collection.update_one(
            {"application_id": app_id},
            {"$set": data},
            upsert=True,
        )
        found = await step5_and_6_collection.find_one({"application_id": app_id})
        assert found is not None
        assert found["routing_color"] == "GREEN"
        assert found["risk_score"] == 90
        # Cleanup
        await step5_and_6_collection.delete_one({"application_id": app_id})


# ==========================================================================
# 5. Full Pipeline Collection
# ==========================================================================

class TestFullPipelineCollection:
    """Tests full pipeline record persistence."""

    @pytest.mark.asyncio
    async def test_upsert_full_pipeline(self, app_id):
        data = {
            "application_id": app_id,
            "status": "EXTRACTED",
            "declared_monthly_income": 72000.0,
            "requested_loan_amount": 300000.0,
            "validation_report": {"routing_color": "GREEN"},
            "underwriting_decision": {"verdict": "APPROVED"},
        }
        await full_pipeline_collection.update_one(
            {"application_id": app_id},
            {"$set": data},
            upsert=True,
        )
        found = await full_pipeline_collection.find_one({"application_id": app_id})
        assert found is not None
        assert found["status"] == "EXTRACTED"
        assert found["validation_report"]["routing_color"] == "GREEN"
        # Cleanup
        await full_pipeline_collection.delete_one({"application_id": app_id})

    @pytest.mark.asyncio
    async def test_projection_excludes_id(self, app_id):
        data = {"application_id": app_id, "status": "EXTRACTED"}
        await full_pipeline_collection.update_one(
            {"application_id": app_id},
            {"$set": data},
            upsert=True,
        )
        found = await full_pipeline_collection.find_one(
            {"application_id": app_id},
            {"_id": 0},
        )
        assert "_id" not in found
        # Cleanup
        await full_pipeline_collection.delete_one({"application_id": app_id})
