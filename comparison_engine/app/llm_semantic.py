import os
import json
from typing import Any, Dict, List
from langchain_groq import ChatGroq
from .models import SemanticFinding


def semantic_compare(declared: Dict[str, Any], verified: Dict[str, Any]) -> List[SemanticFinding]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return []

    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    llm = ChatGroq(model=model_name, temperature=0, groq_api_key=api_key, max_retries=1)

    prompt = f"""You are a loan-document semantic comparison assistant.
Your task is ONLY to compare textual information for inconsistencies.

Declared information:
{json.dumps(declared, indent=2)}

Verified information:
{json.dumps(verified, indent=2)}

Compare ONLY these fields:
1. Name
2. Employer
3. Purpose

Consider abbreviations (Pvt vs Private, Ltd vs Limited), punctuation, capitalization, and minor spelling differences.

For each field, return:
- field: string
- status: "MATCH" | "PARTIAL_MATCH" | "MISMATCH" | "NOT_AVAILABLE"
- reason: concise explanation
- confidence: number between 0 and 100

Return ONLY valid JSON matching this schema:
{{
  "findings": [
    {{
      "field": "Name",
      "status": "MATCH",
      "reason": "Both records contain matching full name.",
      "confidence": 100
    }}
  ]
}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        findings = []
        for item in data.get("findings", []):
            findings.append(
                SemanticFinding(
                    field=item.get("field", ""),
                    status=item.get("status", "NOT_AVAILABLE"),
                    reason=item.get("reason", ""),
                    confidence=float(item.get("confidence", 0)),
                )
            )
        return findings
    except Exception as e:
        print(f"[WARN] Semantic LLM comparison skipped: {e}")
        return []