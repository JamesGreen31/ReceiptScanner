"""

 Main.py
 
 Simple CLI for testing receipt parsing without the web server.
 Authors: James Green, Chris Duckers, Numi Tesfay
 Supervised by: Dr. Natalia Bell
 Marymount University, Spring 2024
 """
import argparse
import json
import sys
from pathlib import Path

from .processor import ReceiptScanner, ImagePreprocessor, OCRProcessor, TextProcessor


def main(argv=None):
    parser = argparse.ArgumentParser(prog="receiptscanner", description="Simple Receipt Scanner CLI")
    parser.add_argument("paths", nargs="*", help="Image files to parse (paths)")
    parser.add_argument("--no-ocr", dest="use_ocr", action="store_false", help="Disable OCR and use stubbed output")
    args = parser.parse_args(argv)

    if not args.paths:
        print("No input files provided. Use --help for usage.")
        return 1

    # Compose processors and pass them into the scanner so the CLI uses the
    # concrete Image/OCR/Text processors defined in `processor.py`.
    scanner = ReceiptScanner(
        use_ocr=args.use_ocr,
        image_processor=ImagePreprocessor(),
        ocr_processor=OCRProcessor() if args.use_ocr else None,
        text_processor=TextProcessor(),
    )
    results = {}
    for p in args.paths:
        ppth = Path(p)
        try:
            parsed = scanner.parse_image(str(ppth))
        except Exception as exc:
            parsed = {"error": str(exc)}
        results[str(ppth)] = parsed

    json.dump(results, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
