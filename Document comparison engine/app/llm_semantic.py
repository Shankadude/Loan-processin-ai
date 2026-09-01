import os
import json

from langchain_groq import ChatGroq

from .models import SemanticFinding


def semantic_compare(declared, verified):

    api_key = os.getenv("GROQ_API_KEY")

    # If API isn't configured,
    # skip semantic stage.
    if not api_key:
        return []

    model_name = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-20b"
    )

    llm = ChatGroq(
        model=model_name,
        temperature=0
    )

    prompt = f"""
You are a loan-document semantic comparison assistant.

Your task is ONLY to compare textual information.

Do NOT:
- calculate financial risk
- make loan approval decisions
- invent information
- change numeric values

Declared information:

{json.dumps(declared, indent=2)}

Verified information:

{json.dumps(verified, indent=2)}

Compare ONLY these fields:

1. Name
2. Employer
3. Purpose

Consider:
- abbreviations
- Pvt vs Private
- Ltd vs Limited
- punctuation
- capitalization
- minor spelling differences

For every field, return:

field
status
reason
confidence

status MUST be exactly one of:

MATCH
PARTIAL_MATCH
MISMATCH
NOT_AVAILABLE

confidence MUST be a number between 0 and 100.

IMPORTANT:
Return ONLY valid JSON.
Do NOT use markdown.
Do NOT use ```json.
Do NOT include any explanation outside the JSON.

The JSON must have exactly this structure:

{{
    "findings": [
        {{
            "field": "Name",
            "status": "MATCH",
            "reason": "Both records contain the same name.",
            "confidence": 100
        }}
    ]
}}
"""

    response = llm.invoke(prompt)

    # Get model response
    content = response.content

    # Sometimes the model may return surrounding whitespace
    content = content.strip()

    # Remove markdown fences if the model accidentally adds them
    if content.startswith("```json"):
        content = content[7:]

    if content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        data = json.loads(content)

    except json.JSONDecodeError as e:

        print("ERROR: LLM returned invalid JSON")
        print("LLM response:")
        print(content)

        raise e

    findings = []

    for item in data.get("findings", []):

        findings.append(

            SemanticFinding(

                field=item.get(
                    "field",
                    ""
                ),

                status=item.get(
                    "status",
                    "NOT_AVAILABLE"
                ),

                reason=item.get(
                    "reason",
                    ""
                ),

                confidence=float(
                    item.get(
                        "confidence",
                        0
                    )
                )
            )
        )

    return findings