import asyncio
from src.workflow import create_loan_pipeline_graph
from test_agents import create_dummy_pan_image

async def run_integration_test():
    print("🚀 Initializing compiled LangGraph pipeline...")
    app = create_loan_pipeline_graph()

    dummy_pan_bytes = create_dummy_pan_image()

    test_payload = {
        "application_id": "test-app-001",
        "declared_monthly_income": 95000.0,
        "requested_loan_amount": 500000.0,
        "raw_files": [
            {"filename": "pan_card.png", "bytes": dummy_pan_bytes}
        ]
    }

    print("⚙️ Executing graph nodes...")
    final_output = await app.ainvoke(test_payload)

    print("\n✅ Extracted Documents Count:", len(final_output["extracted_docs"]))
    print("✅ Validation Status:", final_output["validation_report"].validation_status)
    print("✅ Underwriting Verdict:", final_output["underwriting_decision"].verdict)
    print("📝 Rationale:", final_output["underwriting_decision"].executive_rationale)

if __name__ == "__main__":
    asyncio.run(run_integration_test())