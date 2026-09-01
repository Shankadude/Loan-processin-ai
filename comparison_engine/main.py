from pathlib import Path

from dotenv import load_dotenv

from app.database import (
    get_all_applications,
    update_comparison_result,
)

from app.pipeline import (
    build_pipeline_result,
)


load_dotenv()


OUTPUT_DIR = Path(
    "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def main():

    print("=" * 60)

    print(
        "LOAN APPLICATION COMPARISON ENGINE"
    )

    print("=" * 60)


    # =====================================================
    # FETCH APPLICATIONS
    # =====================================================

    print(
        "\nFetching applications from MongoDB..."
    )

    applications = (
        get_all_applications()
    )

    print(
        f"Found {len(applications)} applications."
    )


    successful = 0

    failed = 0


    # =====================================================
    # PROCESS EACH APPLICATION
    # =====================================================

    for payload in applications:

        application_id = payload.get(
            "_id"
        )

        print(
            "\n"
            + "=" * 60
        )

        print(
            f"Processing application: "
            f"{application_id}"
        )

        print(
            "=" * 60
        )


        try:

            print(
                "Running declared-vs-verified comparison..."
            )


            # RUN PIPELINE

            result = (
                build_pipeline_result(
                    payload
                )
            )


            # CONVERT TO DICTIONARY

            result_dict = (
                result.model_dump()
            )


            # SAVE TO MONGODB

            update_comparison_result(

                application_id,

                result_dict,
            )


            print(
                "✓ Comparison result stored in MongoDB."
            )


            # SAVE LOCAL JSON

            output_file = (
                OUTPUT_DIR
                / (
                    f"comparison_result_"
                    f"{application_id}.json"
                )
            )


            with open(
                output_file,
                "w",
                encoding="utf-8",
            ) as f:

                f.write(
                    result.model_dump_json(
                        indent=2
                    )
                )


            print(
                f"✓ Result saved locally: "
                f"{output_file}"
            )


            # DISPLAY RESULT

            print(
                f"Overall Status: "
                f"{result.overall_status}"
            )

            print(
                f"Identity Status: "
                f"{result.identity_status}"
            )

            print(
                f"Income Status: "
                f"{result.income_status}"
            )

            print(
                f"Liability Status: "
                f"{result.liability_status}"
            )

            print(
                f"Declared Income: "
                f"Rs. {result.declared_monthly_net:,.2f}"
            )

            print(
                f"Verified Income: "
                f"Rs. {result.verified_monthly_net:,.2f}"
            )

            print(
                f"Declared EMI: "
                f"Rs. {result.declared_emi:,.2f}"
            )

            print(
                f"Detected EMI: "
                f"Rs. {result.detected_emi:,.2f}"
            )

            print(
                f"DTI: "
                f"{result.dti_percent}%"
            )

            print(
                f"Anomalies: "
                f"{result.anomalies}"
            )


            successful += 1


        except Exception as e:

            print(
                "\n✗ ERROR processing application "
                f"{application_id}"
            )

            print(
                f"Error: {e}"
            )

            failed += 1


    # =====================================================
    # SUMMARY
    # =====================================================

    print(
        "\n"
        + "=" * 60
    )

    print(
        "PROCESSING COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        f"Total applications: "
        f"{len(applications)}"
    )

    print(
        f"Successful: "
        f"{successful}"
    )

    print(
        f"Failed: "
        f"{failed}"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":

    main()