"""Base parser interface. All document parsers must implement this."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from google import genai
from app.core.config import settings


def gemini_extract(prompt: str, text: str) -> str:
    """Utility: call Gemini to extract structured data from OCR text."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    full_prompt = f"{prompt}\n\nDocument text:\n{text[:6000]}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )
    return response.text.strip()


class BaseParser(ABC):
    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        pass
