import json
from typing import Dict, Any
from app.parsers.base import BaseParser, gemini_extract


class InvoiceParser(BaseParser):
    def parse(self, text: str) -> Dict[str, Any]:
        prompt = """Extract the following fields from this invoice document and return as valid JSON.
Use null for any fields not found.

Required JSON format:
{
  "invoice_number": "...",
  "invoice_date": "...",
  "vendor_name": "...",
  "customer_name": "...",
  "gst_number": "...",
  "invoice_amount": "...",
  "tax_amount": "...",
  "line_items": [
    {"description": "...", "quantity": "...", "unit_price": "...", "amount": "..."}
  ]
}

Return ONLY the JSON object, no markdown, no explanation."""
        try:
            raw = gemini_extract(prompt, text)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception as e:
            return {"error": str(e), "raw_text": text[:500]}
