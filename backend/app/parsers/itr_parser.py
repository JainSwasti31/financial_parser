import json
import re
from typing import Dict, Any
from app.parsers.base import BaseParser, gemini_extract


class ITRParser(BaseParser):
    @staticmethod
    def _fallback_extract(text: str) -> Dict[str, Any]:
        amount = r"((?:(?:INR|Rs\.?)\s*|₹\s*)?[+-]?[\d,]+(?:\.\d{1,2})?)"
        patterns = {
            "pan": r"\b([A-Z]{5}[0-9]{4}[A-Z])\b",
            "assessment_year": r"(?:assessment\s+year|\bAY)\s*[:\-]?\s*(\d{4}\s*[-/]\s*(?:\d{2}|\d{4}))",
            "gross_income": rf"(?:gross\s+total\s+income|gross\s+income)\s*[:\-]?\s*{amount}",
            "tax_paid": rf"(?:tax\s+paid(?:\s*\([^\n)]*\))?|total\s+tax\s+paid|tds)\s*[:\-]?\s*{amount}",
            "refund": rf"refund(?:\s+amount)?\s*[:\-]?\s*{amount}",
            "total_deductions": rf"(?:total\s+deductions?(?:\s*\([^\n)]*\))?|deductions?\s+under\s+chapter\s+vi-a)\s*[:\-]?\s*{amount}",
            "taxable_income": rf"(?:total\s+taxable\s+income|taxable\s+income)\s*[:\-]?\s*{amount}",
        }
        fields = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            fields[field] = match.group(1).strip() if match else None
        if fields.get("pan"):
            fields["pan"] = fields["pan"].upper()
        return fields

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
            extracted = json.loads(raw)
            for field, value in self._fallback_extract(text).items():
                if extracted.get(field) in (None, "") and value is not None:
                    extracted[field] = value
            return extracted
        except Exception as e:
            fallback = self._fallback_extract(text)
            if any(value is not None for value in fallback.values()):
                return fallback
            return {"error": str(e), "raw_text": text[:500]}
