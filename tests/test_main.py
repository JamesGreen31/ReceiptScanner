from importlib import import_module
from pathlib import Path
import sys


def test_processor_stub_output():
    # Ensure src is on sys.path so the package imports correctly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    mod = import_module("marymount.edu.receiptscanner.processor")
    scanner = mod.ReceiptScanner(use_ocr=False)
    res = scanner.parse_image("dummy-path.jpg")
    assert isinstance(res, dict)
    assert "merchant" in res and "total" in res and "date" in res
