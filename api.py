import uuid
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from src.workflow import create_loan_pipeline_graph
from src.database.mongo import applications_collection, verified_collection

app = FastAPI(title="Loan Document Processing Engine API")
pipeline = create_loan_pipeline_graph()

# I made this for testing purposes, You can go ahead and use your own code just make sure to use the same variables.
# I advise use AI for smooth code transition.

@app.get("/")
def health_check():
    return {"status": "online", "service": "Loan Document Processing Engine"}

@app.post("/api/process-loan-application/")
async def process_loan_application(
    declared_income: float = Form(...),
    requested_amount: float = Form(...),
    files: List[UploadFile] = File(...)
):
    """Entrypoint: Ingests documents and executes the LangGraph agent pipeline."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    application_id = str(uuid.uuid4())
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

    try:
        print(f" Executing LangGraph for Application ID: {application_id} ({len(files)} files)...")
        final_state = await pipeline.ainvoke(initial_state)

        # Convert Pydantic objects safely if present
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

        response_data = {
            "application_id": application_id,
            "declared_monthly_income": declared_income,
            "requested_loan_amount": requested_amount,
            "extracted_documents": final_state.get("extracted_docs", []),
            "validation_report": validation_data,
            "underwriting_decision": decision_data,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        # Safe DB Insertion: Use .copy() so Mongo's inserted _id does not mutate response_data
        try:
            db_payload = response_data.copy()
            await applications_collection.insert_one(db_payload)
            print(" Application record saved to MongoDB.")
        except Exception as db_err:
            print(f" Warning: MongoDB write skipped or failed: {db_err}")

        return response_data

    except Exception as e:
        print("\n Pipeline Processing Exception:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


class HumanOverridePayload(BaseModel):
    application_id: str
    filename: str
    original_extracted_data: Dict[str, Any]
    verified_data: Dict[str, Any]

@app.post("/api/save-verified-document/")
async def save_verified_document(payload: HumanOverridePayload):
    """Saves underwriter edits and human verification overrides to MongoDB."""
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
        print(f" DB save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))