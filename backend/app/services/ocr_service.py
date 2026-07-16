"""
OCR Service — Swappable interface for text extraction.
Provider is selected via OCR_PROVIDER env var:
  - "gemini"    (default) — uses Google Gemini Vision API
  - "tesseract" — local Tesseract OCR (free, offline)
"""
import os
import time
import logging

logger = logging.getLogger(__name__)

# Gemini model fallback chain (try each on quota/error)
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
import base64
from abc import ABC, abstractmethod
from typing import Tuple

from app.core.config import settings

# ─── Abstract Interface ────────────────────────────────────────────────────────

class OCRProvider(ABC):
    @abstractmethod
    def extract_text(self, file_path: str, mime_type: str) -> Tuple[str, float]:
        """Returns (extracted_text, duration_seconds)"""
        pass


# ─── Gemini Provider ───────────────────────────────────────────────────────────

class GeminiOCRProvider(OCRProvider):
    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _file_to_base64(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _pdf_to_images_base64(self, file_path: str) -> list:
        """Convert PDF pages to base64 images using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            images = []
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
            doc.close()
            return images
        except Exception as e:
            raise RuntimeError(f"Failed to render PDF pages: {e}")

    def _call_gemini(self, contents: list) -> str:
        """Try each model in fallback chain, with retry on 429."""
        last_err = None
        for model in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents
                    )
                    return response.text
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        wait = (2 ** attempt) * 10  # 10s, 20s, 40s
                        logger.warning(f"Gemini 429 on {model}, waiting {wait}s...")
                        time.sleep(wait)
                        last_err = e
                    else:
                        last_err = e
                        break  # Non-quota error — try next model
        raise RuntimeError(f"All Gemini models exhausted: {last_err}")

    def extract_text(self, file_path: str, mime_type: str) -> Tuple[str, float]:
        from google.genai import types

        start = time.time()
        ext = os.path.splitext(file_path)[1].lower()

        prompt = (
            "You are an expert OCR system. Extract ALL text from this financial document "
            "exactly as it appears. Preserve tables, numbers, dates, and formatting. "
            "Do not summarize — output raw extracted text only."
        )

        try:
            if ext == ".pdf":
                images = self._pdf_to_images_base64(file_path)
                all_text = []
                for i, img_b64 in enumerate(images):
                    contents = [
                        types.Part.from_bytes(
                            data=base64.b64decode(img_b64),
                            mime_type="image/png"
                        ),
                        f"Page {i+1}: {prompt}"
                    ]
                    page_text = self._call_gemini(contents)
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
                text = "\n\n".join(all_text)
            else:
                img_b64 = self._file_to_base64(file_path)
                contents = [
                    types.Part.from_bytes(
                        data=base64.b64decode(img_b64),
                        mime_type=mime_type
                    ),
                    prompt
                ]
                text = self._call_gemini(contents)

        except Exception as e:
            raise RuntimeError(f"Gemini OCR failed: {e}")

        duration = time.time() - start
        return text.strip(), duration


# ─── Tesseract Provider (Fallback) ─────────────────────────────────────────────

class TesseractOCRProvider(OCRProvider):
    def extract_text(self, file_path: str, mime_type: str) -> Tuple[str, float]:
        import pytesseract
        from PIL import Image
        start = time.time()
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".pdf":
                import fitz
                doc = fitz.open(file_path)
                all_text = []
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img, config="--psm 6")
                    all_text.append(f"--- Page {i+1} ---\n{page_text}")
                doc.close()
                text = "\n\n".join(all_text)
            else:
                img = Image.open(file_path)
                text = pytesseract.image_to_string(img, config="--psm 6")

        except Exception as e:
            raise RuntimeError(f"Tesseract OCR failed: {e}")

        duration = time.time() - start
        return text.strip(), duration


# ─── Factory ───────────────────────────────────────────────────────────────────

def get_ocr_provider() -> OCRProvider:
    provider = getattr(settings, "OCR_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiOCRProvider()
    elif provider == "tesseract":
        return TesseractOCRProvider()
    else:
        # Default fallback
        return GeminiOCRProvider()
