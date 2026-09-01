from fastapi import (
    APIRouter,
    HTTPException,
)

from database.db_config import get_db
from database import crud

from decision_engine.pipeline import (
    run_decision_pipeline,
)


router = APIRouter(
    prefix="/applications",
    tags=["Loan Applications"]
)


# ============================================================
# PROCESS APPLICATION
# ============================================================

@router.post(
    "/{application_id}/process"
)
def process_application(
    application_id: str
):

    db = get_db()

    application = crud.get_application(
        db,
        application_id
    )

    if not application:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Application "
                f"'{application_id}' not found."
            )
        )

    try:

        result = run_decision_pipeline(
            application_id=application_id,
            db=db
        )

        return {
            "success": True,

            "application_id": (
                application_id
            ),

            "status": (
                result.status
            ),

            "routing_color": (
                result.routing_color
            ),

            "recommendation": (
                result.recommendation
            ),

            "risk_score": (
                result.risk_score
            ),

            "risk_grade": (
                result.risk_grade
            ),

            "underwriting_summary": (
                result.underwriting_summary
            ),
        }

    except Exception as e:

        crud.update_pipeline_error(
            db,
            application_id,
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Decision pipeline failed: {str(e)}"
            )
        )


# ============================================================
# GET FINAL DECISION
# ============================================================

@router.get(
    "/{application_id}/decision"
)
def get_decision(
    application_id: str
):

    db = get_db()

    result = crud.get_decision_result(
        db,
        application_id
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No decision found for "
                f"application '{application_id}'."
            )
        )

    return {
        "success": True,
        "data": result
    }