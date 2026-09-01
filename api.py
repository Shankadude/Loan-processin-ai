import uuid
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from src.workflow import create_loan_pipeline_graph
from src.utils.assembly import find_missing_documents, build_applicant_block
from src.database.mongo import applications_collection, verified_collection

app = FastAPI(title="Loan Document Processing Engine API")
pipeline = create_loan_pipeline_graph()


@app.get("/")
def health_check():
    return {"status": "online", "service": "Loan Document Processing Engine"}


# --- Core Pipeline Execution Helper ---
async def execute_loan_workflow(
    application_id: str,
    declared_income: float,
    requested_amount: float,
    files: List[UploadFile]
) -> Dict[str, Any]:
    raw_files = []
    for file in files:
        content = await file.read()
        raw_files.append({
            "filename": file.filename,
            "bytes": content
        })

    initial_state = {
        "application_id": application_id,
        "declared_monthly_income": declared_income,
        "requested_loan_amount": requested_amount,
        "raw_files": raw_files
    }

    final_state = await pipeline.ainvoke(initial_state)
    extracted_docs = final_state.get("extracted_docs", [])

    # Check for missing required documentation
    missing_docs = find_missing_documents(extracted_docs)
    status = "INCOMPLETE" if missing_docs else "EXTRACTED"

    validation_data = (
        final_state["validation_report"].model_dump()
        if hasattr(final_state.get("validation_report"), "model_dump")
        else final_state.get("validation_report", {})
    )
    decision_data = (
        final_state["underwriting_decision"].model_dump()
        if hasattr(final_state.get("underwriting_decision"), "model_dump")
        else final_state.get("underwriting_decision", {})
    )

    return {
        "application_id": application_id,
        "status": status,
        "missing_documents": missing_docs,
        "declared_monthly_income": declared_income,
        "requested_loan_amount": requested_amount,
        "extracted_documents": extracted_docs,
        "validation_report": validation_data,
        "underwriting_decision": decision_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


# ==========================================
# 1. Primary Ingestion Endpoints
# ==========================================

@app.post("/api/process-loan-application/")
@app.post("/applications")
async def create_application(
    declared_income: float = Form(0.0),
    requested_amount: float = Form(0.0),
    files: List[UploadFile] = File(...)
):
    """Processes uploaded documents through LangGraph and tracks completeness."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    application_id = "APP-" + str(uuid.uuid4())[:8]

    try:
        response_data = await execute_loan_workflow(
            application_id=application_id,
            declared_income=declared_income,
            requested_amount=requested_amount,
            files=files
        )

        # Persist copy to MongoDB
        try:
            db_payload = dict(response_data)
            await applications_collection.insert_one(db_payload)
        except Exception as db_err:
            print(f"⚠️ Warning: MongoDB write failed: {db_err}")

        # Return clean response without internal Mongo _id
        response_data.pop("_id", None)
        return response_data

    except Exception as e:
        print("❌ Pipeline Processing Exception:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/applications/{application_id}/documents")
async def add_more_documents(
    application_id: str,
    files: List[UploadFile] = File(...)
):
    """Appends missing documents to an existing application record."""
    existing_app = await applications_collection.find_one({"application_id": application_id})
    if not existing_app:
        raise HTTPException(status_code=404, detail="Application ID not found.")

    if not files:
        raise HTTPException(status_code=400, detail="No new files provided.")

    try:
        new_result = await execute_loan_workflow(
            application_id=application_id,
            declared_income=existing_app.get("declared_monthly_income", 0.0),
            requested_amount=existing_app.get("requested_loan_amount", 0.0),
            files=files
        )

        all_docs = existing_app.get("extracted_documents", []) + new_result.get("extracted_documents", [])
        missing_docs = find_missing_documents(all_docs)
        status = "INCOMPLETE" if missing_docs else "EXTRACTED"

        update_fields = {
            "status": status,
            "missing_documents": missing_docs,
            "extracted_documents": all_docs,
            "validation_report": new_result.get("validation_report"),
            "underwriting_decision": new_result.get("underwriting_decision"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        await applications_collection.update_one(
            {"application_id": application_id},
            {"$set": update_fields}
        )

        updated_record = await applications_collection.find_one(
            {"application_id": application_id},
            {"_id": 0}
        )
        return updated_record

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Incremental processing error: {str(e)}")


@app.get("/applications/{application_id}")
async def get_application_details(application_id: str):
    """Retrieves full application status and audit history."""
    app_doc = await applications_collection.find_one(
        {"application_id": application_id},
        {"_id": 0}
    )
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app_doc


# ==========================================
# 2. Human-In-The-Loop Verification
# ==========================================

class HumanOverridePayload(BaseModel):
    application_id: str
    filename: str
    original_extracted_data: Dict[str, Any]
    verified_data: Dict[str, Any]


@app.post("/api/save-verified-document/")
async def save_verified_document(payload: HumanOverridePayload):
    """Saves human edits and logs audit trail in MongoDB."""
    try:
        await verified_collection.update_many(
            {"application_id": payload.application_id, "filename": payload.filename, "is_active": True},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )

        record = {
            "application_id": payload.application_id,
            "filename": payload.filename,
            "original_extracted_data": payload.original_extracted_data,
            "verified_data": payload.verified_data,
            "verified_at": datetime.now(timezone.utc),
            "is_active": True
        }
        res = await verified_collection.insert_one(record)
        return {"status": "success", "id": str(res.inserted_id)}
    except Exception as e:
        print(f"❌ DB save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))