"""
AI Classification Service — Swappable interface for document type classification.
Provider is selected via AI_PROVIDER env var:
  - "gemini"     (default) — uses Google Gemini API
  - "rule_based" — keyword/regex heuristic classifier (no API needed)
  - "openai"     — plug in later with OPENAI_API_KEY
"""
import re
from typing import Any
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback model chain
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

DOCUMENT_TYPES = [
    "Bank Statement",
    "Invoice",
    "Salary Slip",
    "GST Return",
    "ITR",
    "Balance Sheet",
    "Profit & Loss",
]

# ─── Abstract Interface ────────────────────────────────────────────────────────

class AIClassifier(ABC):
    @abstractmethod
    def classify(self, text: str) -> str:
        """Returns one of the DOCUMENT_TYPES or 'Unknown'."""
        pass


# ─── Gemini Classifier ─────────────────────────────────────────────────────────

class GeminiClassifier(AIClassifier):
    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def classify(self, text: str) -> str:
        prompt = f"""You are a financial document classifier.
Classify the following extracted document text into EXACTLY ONE of these categories:
{', '.join(DOCUMENT_TYPES)}

Rules:
- Return ONLY the category name, nothing else.
- If the document doesn't match any category, return "Unknown".
- Base your decision on the content, keywords, and structure.

Document text (first 3000 chars):
{text[:3000]}

Category:"""
        last_err = None
        for model in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    result = response.text.strip()
                    for dtype in DOCUMENT_TYPES:
                        if dtype.lower() in result.lower():
                            return dtype
                    return "Unknown"
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        wait = (2 ** attempt) * 10
                        logger.warning(f"Gemini 429 on {model} (classify), waiting {wait}s...")
                        time.sleep(wait)
                        last_err = e
                    else:
                        last_err = e
                        break
        # All models exhausted — fall back to rule-based
        logger.error(f"Gemini classifier exhausted, falling back to rule-based: {last_err}")
        return RuleBasedClassifier().classify(text)


# ─── Rule-Based Classifier (Fallback) ──────────────────────────────────────────

class RuleBasedClassifier(AIClassifier):
    RULES = {
        "Bank Statement": [
            r"account\s+statement", r"bank\s+statement", r"transaction\s+history",
            r"opening\s+balance", r"closing\s+balance", r"ifsc", r"account\s+number"
        ],
        "Invoice": [
            r"invoice\s+number", r"invoice\s+date", r"bill\s+to", r"vendor",
            r"total\s+amount", r"gst\s+number", r"hsn\s+code", r"line\s+item"
        ],
        "Salary Slip": [
            r"salary\s+slip", r"pay\s+slip", r"payslip", r"employee\s+id",
            r"gross\s+salary", r"net\s+salary", r"pf\s+deduction", r"professional\s+tax"
        ],
        "GST Return": [
            r"gst\s+return", r"gstin", r"gstr", r"cgst", r"sgst", r"igst",
            r"taxable\s+value", r"filing\s+period"
        ],
        "ITR": [
            r"income\s+tax\s+return", r"itr", r"assessment\s+year", r"pan\b",
            r"gross\s+total\s+income", r"tax\s+payable", r"refund"
        ],
        "Balance Sheet": [
            r"balance\s+sheet", r"total\s+assets", r"total\s+liabilities",
            r"shareholders\s+equity", r"current\s+assets", r"fixed\s+assets"
        ],
        "Profit & Loss": [
            r"profit\s+and\s+loss", r"p&l", r"revenue", r"gross\s+profit",
            r"operating\s+expenses", r"net\s+profit", r"ebitda"
        ],
    }

    def classify(self, text: str) -> str:
        text_lower = text.lower()
        scores = {}
        for doc_type, patterns in self.RULES.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            scores[doc_type] = score

        best_type = max(scores, key=scores.get)
        if scores[best_type] >= 2:
            return best_type
        return "Unknown"


# ─── Factory ───────────────────────────────────────────────────────────────────

def get_ai_classifier() -> AIClassifier:
    provider = getattr(settings, "AI_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiClassifier()
    elif provider == "rule_based":
        return RuleBasedClassifier()
    else:
        return GeminiClassifier()


def calculate_field_confidences(parsed_fields: dict[str, Any], raw_text: str, validations: dict) -> dict[str, int]:
    """Return explainable 0-100 confidence scores for extracted fields."""
    normalized_text = re.sub(r"\s+", " ", raw_text or "").casefold()
    scores = {}
    for field, value in parsed_fields.items():
        if value in (None, "", [], {}):
            scores[field] = 0
            continue
        validation = validations.get(field, {})
        status = validation.get("status")
        score = 82
        if status == "valid":
            score = 94
        elif status == "invalid":
            score = 42
        elif status == "missing":
            score = 0
        display = str(value).strip().casefold()
        if display and display in normalized_text:
            score = min(100, score + 4)
        if isinstance(value, (list, dict)):
            score = min(score, 85)
        scores[field] = int(score)
    return scores
