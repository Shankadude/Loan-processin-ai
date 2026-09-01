
from pathlib import Path

from dotenv import load_dotenv

from app.database import (
    get_all_applications,
    update_comparison_result,
)

from app.pipeline import build_pipeline_result

load_dotenv()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 60)
    print("LOAN APPLICATION COMPARISON ENGINE")
    print("=" * 60)

    print("\nFetching applications from MongoDB...")

    applications = get_all_applications()

    print(f"Found {len(applications)} applications.")

    successful = 0
    failed = 0

    for payload in applications:
        application_id = payload.get("_id")

        print("\n" + "=" * 60)
        print(f"Processing application: {application_id}")
        print("=" * 60)

        try:
            # RUN COMPARISON PIPELINE

            print("Running declared-vs-verified comparison...")

            result = build_pipeline_result(payload)

            # CONVERT RESULT TO DICTIONARY

            result_dict = result.model_dump()

            # SAVE RESULT TO MONGODB

            update_comparison_result(
                application_id,
                result_dict,
            )

            print("✓ Comparison result stored in MongoDB.")

            output_file = (
                OUTPUT_DIR
                / f"comparison_result_{application_id}.json"
            )

            with open(
                output_file,
                "w",
                encoding="utf-8",
            ) as f:
                f.write(
                    result.model_dump_json(indent=2)
                )

            print(f"✓ Result saved locally: {output_file}")

            print(f"Overall Status: {result.overall_status}")
            print(f"Risk Level: {result.risk_level}")
            print(f"Recommendation: {result.recommendation}")

            successful += 1

        except Exception as e:
            print(
                f"\n✗ ERROR processing application "
                f"{application_id}"
            )
            print(f"Error: {e}")

            failed += 1

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)

    print(f"Total applications: {len(applications)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    print("=" * 60)

if __name__ == "__main__":
    main()