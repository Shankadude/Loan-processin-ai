from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


APPLICATION_COLLECTION = "loan_applications"


def get_application(
    db: Database,
    application_id: str
) -> dict | None:

    return db[APPLICATION_COLLECTION].find_one(
        {"_id": application_id}
    )


def get_all_applications(
    db: Database
) -> list[dict]:

    return list(
        db[APPLICATION_COLLECTION].find({})
    )


def update_comparison_result(
    db: Database,
    application_id: str,
    comparison_result: dict
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$set": {
                "comparison_status": "COMPLETED",
                "comparison_result": comparison_result,
                "comparison_completed_at": datetime.now(timezone.utc)
            }
        }
    )


def update_risk_assessment(
    db: Database,
    application_id: str,
    risk_assessment: dict
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$set": {
                "risk_assessment_status": "COMPLETED",
                "risk_assessment": risk_assessment,
                "risk_assessment_completed_at": datetime.now(timezone.utc)
            }
        }
    )


def update_risk_result(
    db: Database,
    application_id: str,
    risk_result: dict
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$set": {
                "risk_result": risk_result,
                "risk_completed_at": datetime.now(timezone.utc)
            }
        }
    )


def update_final_decision(
    db: Database,
    application_id: str,
    decision: dict
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$set": {
                "decision": decision,
                "decision_status": "COMPLETED",
                "decision_completed_at": datetime.now(timezone.utc)
            }
        }
    )


def update_pipeline_error(
    db: Database,
    application_id: str,
    error_message: str
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$set": {
                "decision_status": "FAILED",
                "decision_error": error_message,
                "decision_failed_at": datetime.now(timezone.utc)
            }
        }
    )


def get_decision_result(
    db: Database,
    application_id: str
) -> dict | None:

    document = db[APPLICATION_COLLECTION].find_one(
        {"_id": application_id},
        {
            "_id": 1,
            "application_ref": 1,
            "comparison_result": 1,
            "risk_assessment": 1,
            "risk_result": 1,
            "decision": 1,
            "decision_status": 1,
            "comparison_status": 1,
            "risk_assessment_status": 1
        }
    )

    return document


def log_audit_event(
    db: Database,
    application_id: str,
    action: str,
    detail: dict[str, Any]
) -> None:

    db[APPLICATION_COLLECTION].update_one(
        {"_id": application_id},
        {
            "$push": {
                "audit_log": {
                    "action": action,
                    "detail": detail,
                    "timestamp": datetime.now(timezone.utc)
                }
            }
        }
    )