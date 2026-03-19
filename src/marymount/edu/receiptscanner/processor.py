"""Minimal receipt processor frame.

This file intentionally contains a very small, stable frame for the
`ReceiptScanner` and a lightweight `receipts_dataframe` helper. The goal
is to provide a clear starting point for implementing parsing logic while
keeping callers (CLI / web) working against a predictable API.
"""
from __future__ import annotations

from typing import Dict, Any, List


class ImagePreprocessor:
    def preprocess(self, image_path: str) -> str:
        """Return a path to a preprocessed image."""
        return image_path


class OCRProcessor:
    def extract_text(self, image_path: str) -> str:
        """Return extracted text from the given image path."""
        return f"Extracted text from {image_path}"


class TextProcessor:
    def parse_text(self, text: str) -> Dict[str, Any]:
        """Return a structured dict of parsed data from the given text."""
        return {
            "merchant": "ACME Store",
            "date": "1970-01-01",
            "total": "0.00",
            "lines": [f"Parsed line from text: {text}"],
        }


class ReceiptScanner:
    def __init__(
        self,
        use_ocr: bool = True,
        image_processor: ImagePreprocessor | None = None,
        ocr_processor: OCRProcessor | None = None,
        text_processor: TextProcessor | None = None,
    ):
        self.use_ocr = use_ocr
        self.image_processor = image_processor or ImagePreprocessor()
        self.ocr_processor = ocr_processor or OCRProcessor()
        self.text_processor = text_processor or TextProcessor()

    def parse_image(self, image_path: str) -> Dict[str, Any]:
        preprocessed = self.image_processor.preprocess(image_path)

        if self.use_ocr:
            text = self.ocr_processor.extract_text(preprocessed)
        else:
            text = f"Stubbed text for {image_path}"

        return self.text_processor.parse_text(text)


def _parse_amount_to_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return 0.0


def receipts_dataframe(store: Dict[str, Dict[str, Any]]) -> List[Dict[str, object]]:
    """Convert the in-memory STORE mapping to a normalized list of records."""
    records: List[Dict[str, object]] = []

    for uid, v in store.items():
        res = v.get("result") or {}
        merchant = res.get("merchant") if isinstance(res, dict) else None
        date = res.get("date") if isinstance(res, dict) else None
        total_raw = res.get("total") if isinstance(res, dict) else None
        total = _parse_amount_to_float(total_raw)

        broken = (
            merchant in (None, "", "Unknown")
            or date in (None, "")
            or total == 0.0
        )

        rec = {
            "id": uid,
            "filename": v.get("filename"),
            "status": v.get("status"),
            "merchant": merchant,
            "date": date,
            "total": total,
            "error": res.get("error") if isinstance(res, dict) else None,
            "broken": broken,
            "manual": bool(v.get("manual", False)),
            "fixed": bool(v.get("fixed", False)),
        }
        records.append(rec)

    return records