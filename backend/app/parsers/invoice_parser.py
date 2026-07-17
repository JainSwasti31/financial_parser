import json
import logging
import re
from typing import Dict, Any
from app.parsers.base import BaseParser, gemini_extract

logger = logging.getLogger(__name__)

IDENTIFIER_FIELDS = ("gst_number", "pan", "ifsc_code", "account_number")

IDENTIFIER_ALIASES = {
    "gst_number": ("gstin", "gst_no", "gstin_number", "vendor_gstin", "vendor_gst_number"),
    "pan": ("pan_number", "pan_no", "vendor_pan", "vendor_pan_number"),
    "ifsc_code": ("ifsc", "ifsc_number", "bank_ifsc", "vendor_ifsc"),
    "account_number": ("account_no", "bank_account_number", "bank_account_no", "vendor_account_number"),
}

IDENTIFIER_LABELS = {
    "gst_number": r"(?:GSTIN|GST\s*(?:Number|No\.?))",
    "pan": r"(?:PAN\s*(?:Number|No\.?)?)",
    "ifsc_code": r"(?:IFSC\s*(?:Code|Number|No\.?)?)",
    "account_number": r"(?:(?:Bank\s*)?Account\s*(?:Number|No\.?))",
}


def _extract_labeled_identifier(text: str, label_pattern: str):
    """Extract a labeled value without requiring it to already be valid."""
    match = re.search(
        rf"(?im)^\s*{label_pattern}\s*[:#\-]?\s*([^\r\n]+?)\s*$",
        text or "",
    )
    if not match:
        return None
    value = match.group(1).strip().strip("|,;")
    return value or None


def _add_invoice_identifiers(fields: dict, text: str) -> dict:
    """Normalize AI aliases and fill missing identifiers from OCR text."""
    normalized = dict(fields or {})
    for field in IDENTIFIER_FIELDS:
        value = normalized.get(field)
        if value in (None, "", "null"):
            for alias in IDENTIFIER_ALIASES[field]:
                alias_value = normalized.get(alias)
                if alias_value not in (None, "", "null"):
                    value = alias_value
                    break
        if value in (None, "", "null"):
            value = _extract_labeled_identifier(text, IDENTIFIER_LABELS[field])
        normalized[field] = value
    logger.info(
        "Invoice identifier extraction results=%s",
        {field: normalized.get(field) for field in IDENTIFIER_FIELDS},
    )
    return normalized


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
  "pan": "...",
  "ifsc_code": "...",
  "account_number": "...",
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
            return _add_invoice_identifiers(json.loads(raw), text)
        except Exception as e:
            fallback = _add_invoice_identifiers({}, text)
            fallback.update({"error": str(e), "raw_text": text[:500]})
            return fallback
