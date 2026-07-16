import json
from typing import Dict, Any
from app.parsers.base import BaseParser, gemini_extract


class BankStatementParser(BaseParser):
    def parse(self, text: str) -> Dict[str, Any]:
        prompt = """Extract the following fields from this bank statement and return as valid JSON.
Use null for any fields not found.

Required JSON format:
{
  "bank_name": "...",
  "account_holder": "...",
  "account_number": "...",
  "ifsc_code": "...",
  "statement_period": "...",
  "opening_balance": "...",
  "closing_balance": "...",
  "total_credits": "...",
  "total_debits": "...",
  "transaction_count": null,
  "transactions": [
    {"date": "...", "description": "...", "debit": "...", "credit": "...", "balance": "..."}
  ]
}

Return ONLY the JSON object, no markdown, no explanation."""
        try:
            raw = gemini_extract(prompt, text)
            # Strip markdown code fences if present
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception as e:
            return {"error": str(e), "raw_text": text[:500]}
