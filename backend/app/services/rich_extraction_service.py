"""Best-effort table, signature-region, and QR extraction.

Detector failures never fail the core OCR pipeline; they return empty results.
"""
import os
from collections.abc import Callable
from typing import Any


def _detect_qr_and_signatures(image, page_number: int) -> tuple[list[dict], list[dict]]:
    try:
        import cv2
        import numpy as np

        array = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        qr_results = []
        detector = cv2.QRCodeDetector()
        try:
            found, values, points, _ = detector.detectAndDecodeMulti(bgr)
            if found:
                for value, corners in zip(values, points):
                    if value:
                        qr_results.append({"page": page_number, "value": value, "corners": corners.astype(int).tolist()})
        except (AttributeError, ValueError):
            value, corners, _ = detector.detectAndDecode(bgr)
            if value:
                qr_results.append({"page": page_number, "value": value, "corners": corners.astype(int).tolist() if corners is not None else []})

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, ink = cv2.threshold(gray, 165, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = gray.shape
        signatures = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            if y > height * 0.45 and w > width * 0.12 and 2.0 < (w / max(h, 1)) < 15 and area > 100:
                signatures.append({
                    "page": page_number,
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "confidence": min(95, int(55 + area / max(w * h, 1) * 40)),
                })
        return qr_results, signatures[:10]
    except Exception:
        return [], []


def extract_rich_content(
    file_path: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    result = {"tables": [], "signatures": [], "qr_codes": []}
    try:
        from PIL import Image
        extension = os.path.splitext(file_path)[1].lower()
        if extension == ".pdf":
            import fitz
            document = fitz.open(file_path)
            total_pages = len(document)
            for page_index, page in enumerate(document):
                try:
                    finder = page.find_tables()
                    for table_index, table in enumerate(finder.tables):
                        rows = table.extract()
                        if rows:
                            result["tables"].append({"page": page_index + 1, "table": table_index + 1, "rows": rows})
                except Exception:
                    pass
                # Process and release each rendered page immediately. Keeping
                # every page image in a list can exhaust memory on large PDFs.
                pixmap = page.get_pixmap(dpi=150, alpha=False)
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                qr_codes, signatures = _detect_qr_and_signatures(image, page_index + 1)
                result["qr_codes"].extend(qr_codes)
                result["signatures"].extend(signatures)
                image.close()
                del image, pixmap
                if progress_callback:
                    progress_callback(page_index + 1, total_pages)
            document.close()
        else:
            image = Image.open(file_path)
            qr_codes, signatures = _detect_qr_and_signatures(image, 1)
            result["qr_codes"].extend(qr_codes)
            result["signatures"].extend(signatures)
            image.close()
            if progress_callback:
                progress_callback(1, 1)
    except Exception:
        pass
    return result
