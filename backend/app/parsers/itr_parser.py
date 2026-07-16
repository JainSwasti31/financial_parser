import json
from typing import Dict, Any
from app.parsers.base import BaseParser, gemini_extract


class ITRParser(BaseParser):
    def parse(self, text: str) -> Dict[str, Any]:
        prompt = """Extract the following fields from this Income Tax Return (ITR) document and return as valid JSON.
Use null for any fields not found.

Required JSON format:
{
  "pan": "...",
  "assessment_year": "...",
  "gross_income": "...",
  "tax_paid": "...",
  "refund": "...",
  "total_deductions": "...",
  "taxable_income": "..."
}

Return ONLY the JSON object, no markdown, no explanation."""
        try:
            raw = gemini_extract(prompt, text)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception as e:
            return {"error": str(e), "raw_text": text[:500]}
