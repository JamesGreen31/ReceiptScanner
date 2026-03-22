"""
 Processor.py 

 Modularized receipt processing pipeline with image preprocessing, OCR extraction, and text parsing.

 Authors: James Green, Chris Duckers, Numi Tesfay
 Supervised by: Dr. Natalia Bell
 Marymount University, Spring 2024
"""


from __future__ import annotations

from typing import Dict, Any, List, Optional

import re
from pathlib import Path
from PIL import Image, UnidentifiedImageError

"""Optional dependencies for HEIC support and OCR. These are imported with try/except to allow the core pipeline to function even if these are not
installed. See `ImagePreprocessor` and `OCRProcessor` for details."""
try:
    # Optional HEIC support via pillow-heif (if installed)
    import pillow_heif  # type: ignore
    HEIF_AVAILABLE = True
except Exception:
    HEIF_AVAILABLE = False
import os
try:
    import pytesseract
except Exception:
    pytesseract = None

class ImagePreprocessor:
    """Preprocesses receipt images to improve OCR accuracy."""

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".heic"}

    def preprocess(self, image_path: str) -> str:
        path = Path(image_path)

        # Validation: image file exists 
        if not path.exists() or not path.is_file():
            raise ValueError(f"File does not exist: {image_path}")

        # Validation: extension 
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format '{path.suffix}'. "
                f"Supported: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

        # Validation: HEIC support requires pillow-heif
        if suffix == ".heic" and not HEIF_AVAILABLE:
            raise ValueError(
                "HEIC input detected but pillow-heif is not installed. "
                "Install via `pip install pillow-heif` to enable HEIC support."
            )

        try:
            with Image.open(path) as img:
                # Convert to grayscale for improved OCR accuracy (many receipts are black-and-white)
                img = img.convert("L")

                #  Basic normalization
                img = self._normalize(img)

                # Save processed version
                processed_path = path.with_name(f"{path.stem}_processed{path.suffix}")
                img.save(processed_path)

        except UnidentifiedImageError:
            raise ValueError("Invalid or corrupted image file")
        except Exception as e:
            raise RuntimeError(f"Preprocessing failed: {str(e)}")

        return str(processed_path)

    def _normalize(self, img: Image.Image) -> Image.Image:
        """
        Simple min-max contrast normalization.
        """
        extrema = img.getextrema()  # (min, max)
        min_val, max_val = extrema

        if max_val == min_val:
            # Flat image — return as-is (avoid divide-by-zero)
            return img

        # Scale pixels to full 0–255 range
        def scale(p):
            return int((p - min_val) * 255 / (max_val - min_val))

        return img.point(scale)

class OCRProcessor:
    def __init__(
        self,
        tesseract_cmd: str | None = None,
        lang: str = "eng",
        psm: int = 6,
        oem: int = 3,
        ocr_log_dir: str | None = None,
    ) -> None:
        if pytesseract is None:
            raise RuntimeError(
                "OCR support is unavailable because pytesseract is not installed."
            )

        self.lang = lang
        self.psm = psm
        self.oem = oem
        self.ocr_log_dir = ocr_log_dir

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text(self, image_path: str) -> str:
        path = Path(image_path)

        # Safeguard to prevent Tesseract from interacting with an image that does not exist. Failsafe if 
        # preprocessor is bypasses
        if not path.exists() or not path.is_file():
            raise ValueError(f"OCR input file does not exist: {image_path}")

        try:
            with Image.open(path) as img:
                config = f"--oem {self.oem} --psm {self.psm}"
                text = pytesseract.image_to_string(
                    img,
                    lang=self.lang,
                    config=config,
                )
        except UnidentifiedImageError:
            print(f"Failed to open image for OCR: {image_path}")
            raise ValueError("OCR input is not a valid image file")
        except pytesseract.TesseractError as e:
            print(f"Tesseract OCR error for {image_path}: {e}")
            raise RuntimeError(f"Tesseract OCR failed: {e}")
        except Exception as e:
            print(f"Unexpected error during OCR for {image_path}: {e}")
            raise RuntimeError(f"OCR extraction failed: {e}")

        cleaned = self._clean_text(text)

        if not cleaned:
            print(f"OCR completed but no text was extracted from: {image_path}")
            raise ValueError("OCR completed but no text was extracted from the image")

        self._write_ocr_log(path, cleaned)

        return cleaned

    def _write_ocr_log(self, image_path: Path, text: str) -> None:
        try:
            # Default: same directory as image (uploads/)
            print("Writing OCR log for debugging...")
            log_dir = self.ocr_log_dir or image_path.parent
            print(f"OCR log directory: {log_dir}")
            log_dir.mkdir(parents=True, exist_ok=True)

            log_path = log_dir / f"{image_path.stem}_ocr.txt"

            with open(log_path, "w", encoding="utf-8") as f:
                f.write(text)

        except Exception:
            # Logging should NEVER break pipeline
            pass

    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

class TextProcessor:
    AUTHORIZED_VENDORS = {
        "SHELL": ["SHELL"],
        "BP": ["BP"],
        "EXXON": ["EXXON", "EXXONMOBIL", "EXXON MOBIL"],
        "SHEETT": ["SHEETT"],
        "MOBIL": ["MOBIL"],
        "CHEVRON": ["CHEVRON"],
        "SUNOCO": ["SUNOCO"],
        "MARATHON": ["MARATHON"],
        "CIRCLE K": ["CIRCLE K", "CIRCLEK"],
        "7-ELEVEN": ["7-ELEVEN", "7 ELEVEN", "SEVEN ELEVEN"],
        "SPEEDWAY": ["SPEEDWAY"],
        "WAWA": ["WAWA"],
        "SHEETZ": ["SHEETZ"],
        "SUNOCO": ["SUNOCO"],
    }

    AMOUNT_REGEX = re.compile(
        r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2,3})?)"
    )
    GALLONS_REGEX = re.compile(
        r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:g|gal|gallon|gallons)\b",
        re.IGNORECASE
    )


    DATE_REGEX = re.compile(
        r"\b("
        r"(0[1-9]|1[0-2])[/-](0[1-9]|[12][0-9]|3[01])[/-](\d{2}|\d{4})"
        r"|"
        r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
        r")\b"
    )

    def parse_text(self, text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        merchant = self._extract_authorized_vendor(text)
        total = self._extract_total(text)
        date = self._extract_date(text)
        gallons = self._extract_gallons(text)

        # If price-per-gallon not explicitly given, compute using total/gallons
        price_per_gallon: Optional[float] = None
        gallons_source: Optional[str] = None
        try:
            if gallons is not None:
                gallons = float(gallons)
                gallons_source = "ocr"
        except Exception:
            price_per_gallon = None

        price_per_gallon = float(total) / float(gallons)
        ppg_source = "calculated"
        return {
            "merchant": merchant,
            "date": date,
            "total": total,
            "gallons": gallons,
            "gallons_source": gallons_source,
            "price_per_gallon": price_per_gallon,
            "price_per_gallon_source": ppg_source,
            "lines": lines if lines else [text] if text else [],
        }
    def _extract_authorized_vendor(self, text: str) -> str:
        normalized = self._normalize_text(text)

        for canonical_vendor, aliases in self.AUTHORIZED_VENDORS.items():
            for alias in aliases:
                alias_normalized = self._normalize_text(alias)
                if alias_normalized in normalized:
                    return canonical_vendor

        return "Unknown"

    def _extract_total(self, text: str) -> str | None:
        matches = self.AMOUNT_REGEX.findall(text)
        if not matches:
            return None

        values = []
        for m in matches:
            try:
                values.append(float(m.replace(",", "")))
            except Exception:
                pass

        if not values:
            return None

        value = max(values)
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def _extract_date(self, text: str) -> str | None:
        match = self.DATE_REGEX.search(text)
        return match.group(1) if match else None

    def _normalize_text(self, value: str) -> str:
        value = value.upper()
        value = re.sub(r"[^A-Z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _extract_gallons(self, text: str) -> Optional[float]:
        m = self.GALLONS_REGEX.search(text)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None

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
        self.ocr_processor = ocr_processor if use_ocr else None
        if self.use_ocr and self.ocr_processor is None:
            self.ocr_processor = OCRProcessor()
        self.text_processor = text_processor or TextProcessor()

    def parse_image(self, image_path: str) -> Dict[str, Any]:
        preprocessed = self.image_processor.preprocess(image_path)

        if self.use_ocr:
            if self.ocr_processor is None:
                raise RuntimeError("OCR is enabled but no OCR processor is configured.")
            text = self.ocr_processor.extract_text(preprocessed)
        else:
            text = self._demo_text_for_image(image_path)

        return self.text_processor.parse_text(text)

    def _demo_text_for_image(self, image_path: str) -> str:
        return "\n".join([
            "EXXON MOBILE",
            "01/09/2026",
            "$168.730",
            "12.0932 g @ $2.903 /g",
        ])

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
        gallons = None
        if isinstance(res, dict):
            try:
                gallons = float(res.get("gallons")) if res.get("gallons") is not None else None
            except Exception:
                gallons = None

        fixed_flag = bool(v.get("fixed", False))

        # Mark as broken when key fields are missing. If the receipt has been
        # manually fixed (`fixed` flag) we treat it as not broken regardless of
        # missing auto-extracted fields.
        broken = (
            merchant in (None, "", "Unknown")
            or date in (None, "")
            or total == 0.0
            or gallons is None
        ) and not fixed_flag

        rec = {
            "id": uid,
            "filename": v.get("filename"),
            "status": v.get("status"),
            "merchant": merchant,
            "date": date,
            "total": total,
            "gallons": gallons,
            "error": res.get("error") if isinstance(res, dict) else None,
            "broken": broken,
            "fixed": bool(v.get("fixed", False)),
        }
        records.append(rec)

    return records