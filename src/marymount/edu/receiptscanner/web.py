"""
 Web.py

 Simple Flask web server for receipt scanning and management.
 Authors: James Green, Chris Duckers, Numi Tesfay
 Supervised by: Dr. Natalia Bell
 Marymount University, Spring 2024
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, Any

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    send_from_directory,
    abort,
    flash,
)

from .processor import (
    ReceiptScanner,
    receipts_dataframe,
    ImagePreprocessor,
    OCRProcessor,
    TextProcessor,
)
from .service import ReceiptService

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[3]

UPLOAD_DIR = REPO_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
USE_OCR = True

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "dev-secret-key"

DOCS_DIR = REPO_ROOT / "docs" / "_build" / "html"

# Application service layer (wraps in-memory store)
service = ReceiptService(UPLOAD_DIR)
STORE: Dict[str, Dict[str, Any]] = service.store

# Add demo sample items (one good, one broken) for testing
sample_good_id = "sample-good"
sample_broken_id = "sample-broken"

service.store[sample_good_id] = {
    "filename": "sample_good.jpg",
    "status": "done",
    "result": {
        "merchant": "Sample Store",
        "date": "2026-03-14",
        "total": "23.45",
        "lines": ["Sample good receipt"],
    },
    "fixed": False,
    "path": str(UPLOAD_DIR / "sample_good.jpg"),
}

service.store[sample_broken_id] = {
    "filename": "sample_broken.jpg",
    "status": "done",
    "result": {
        "merchant": None,
        "date": None,
        "total": None,
        "lines": ["Broken OCR frame - missing fields"],
    },
    "fixed": False,
    "path": str(UPLOAD_DIR / "sample_broken.jpg"),
}


@app.route("/", methods=["GET"])
def index():
    # Optional collection filter via query param
    collection = request.args.get("collection") or None
    if collection:
        filtered_store = {k: v for k, v in STORE.items() if v.get("collection") == collection}
    else:
        filtered_store = STORE

    records = receipts_dataframe(filtered_store)

    records_map = {str(r.get("id")): r for r in records}
    items = []

    for receipt_id, stored in STORE.items():
        # Skip items not in the current collection filter
        if collection and stored.get("collection") != collection:
            continue
        meta = records_map.get(receipt_id, {})
        item = {"id": receipt_id, **stored}
        item["broken"] = bool(meta.get("broken", stored.get("result") is None))
        item["fixed"] = bool(stored.get("fixed", False))
        items.append(item)

    good_records = [r for r in records if not r.get("broken", False)]
    total_sum = sum(float(r.get("total") or 0.0) for r in good_records)
    total_gallons = sum(float(r.get("gallons") or 0.0) for r in good_records)
    count = len(good_records)

    summary = {
        "count": count,
        "total_sum": f"{total_sum:.2f}",
        "total_gallons": f"{total_gallons:.2f}",
    }


    # Available collections for filtering
    collections = sorted({v.get("collection") for v in STORE.values() if v.get("collection")})

    return render_template("index.html", items=items, summary=summary, collections=collections, current_collection=collection)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please choose a file to upload.")
        return redirect(url_for("index"))

    filename = Path(f.filename).name
    # Keep original filename on disk but prefix with uid to avoid clashes
    uid = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{uid}_{filename}"
    f.save(save_path)

    collection = (request.form.get("collection") or "").strip() or None
    uid = service.add_receipt(save_path, filename, collection=collection)

    scanner = ReceiptScanner(
        use_ocr=USE_OCR,
        image_processor=ImagePreprocessor(),
        ocr_processor=OCRProcessor(),
        text_processor=TextProcessor(),
    )

    try:
        res = scanner.parse_image(str(save_path))
        service.set_result(uid, res, status="done")
    except Exception as exc:
        service.set_result(uid, {"error": str(exc)}, status="error")

    return redirect(url_for("index"))


@app.route("/item/<id>")
def item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404
    return render_template("item.html", id=id, item=it)

@app.route("/item/<id>/preview")
def preview_item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404

    raw_path = it.get("path")
    if not raw_path:
        return "No file available", 404

    original = Path(raw_path)
    processed = original.with_name(f"{original.stem}_processed{original.suffix}")

    if not processed.exists() or not processed.is_file():
        return "Processed preview not found", 404

    try:
        return send_file(processed)
    except Exception:
        return "Processed preview not found", 404

@app.route("/item/<id>/save", methods=["POST"])
def save_item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404
    merchant = (request.form.get("merchant") or "").strip()
    date = (request.form.get("date") or "").strip()
    total = (request.form.get("total") or "").strip()
    lines = (request.form.get("lines") or "").strip()
    gallons = (request.form.get("gallons") or "").strip()
    ppg = (request.form.get("price_per_gallon") or "").strip()

    if not (merchant and date and total):
        flash("Merchant, date and total are required to save/verify.")
        return redirect(url_for("item", id=id))

    result: dict = {
        "merchant": merchant,
        "date": date,
        "total": total,
        "lines": [lines] if lines else [],
    }

    if gallons:
        result["gallons"] = gallons
        result["gallons_source"] = "manual"

    if ppg:
        result["price_per_gallon"] = ppg
        result["price_per_gallon_source"] = "manual"

    # Save through the service to normalize values
    try:
        service.set_result(id, result, status="done")
        service.mark_fixed(id)
    except KeyError:
        return "Not found", 404

    return redirect(url_for("index"))


@app.route("/item/<id>/download")
def download_item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404

    raw_path = it.get("path")
    if not raw_path:
        return "No file available", 404

    path = Path(raw_path)
    if not path.exists() or not path.is_file():
        return "File not found", 404

    try:
        return send_file(path, as_attachment=True, download_name=it.get("filename"))
    except Exception:
        return "File not found", 404


@app.route("/clear", methods=["POST"])
def clear_all():

    STORE.clear()
    service.store[sample_good_id] = {
        "filename": "sample_good.jpg",
        "status": "done",
        "result": {
            "merchant": "Sample Store",
            "date": "2026-03-14",
            "total": "23.45",
            "lines": ["Sample good receipt"],
        },
        "fixed": False,
        "path": str(UPLOAD_DIR / "sample_good.jpg"),
    }

    service.store[sample_broken_id] = {
        "filename": "sample_broken.jpg",
        "status": "done",
        "result": {
            "merchant": None,
            "date": None,
            "total": None,
            "lines": ["Broken OCR frame - missing fields"],
        },
        "fixed": False,
        "path": str(UPLOAD_DIR / "sample_broken.jpg"),
    }
    return redirect(url_for("index"))


@app.route("/docs/")
@app.route("/docs/<path:filename>")
def docs(filename: str = "index.html"):
    """Serve the pre-built Sphinx documentation HTML files."""
    if not DOCS_DIR.exists():
        return "Documentation not built. Run `make -C docs html`.", 404

    target = DOCS_DIR / filename
    if not target.exists():
        return "Not found", 404

    try:
        return send_from_directory(str(DOCS_DIR), filename)
    except Exception:
        abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)