from database.db_config import get_db
from database.crud import get_all_applications

from decision_engine.pipeline import (
    run_decision_pipeline
)


def main():

    db = get_db()

    applications = get_all_applications(
        db
    )

    print(
        f"Found {len(applications)} applications."
    )

    successful = 0
    failed = 0

    for application in applications:

        application_id = application.get(
            "_id"
        )

        print(
            f"\nProcessing {application_id}..."
        )

        try:

            result = run_decision_pipeline(
                application_id,
                db=db
            )

            print(
                f"✓ {application_id}: "
                f"{result.routing_color.upper()} "
                f"| Score: {result.risk_score}"
            )

            successful += 1

        except Exception as e:

            print(
                f"✗ {application_id}: {e}"
            )

            failed += 1

    print("\n==============================")
    print("PROCESSING COMPLETE")
    print("==============================")

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed: {failed}"
    )


if __name__ == "__main__":
    main()