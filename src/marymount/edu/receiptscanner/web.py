"""Minimal Flask web POC for uploading receipts and viewing statuses.

This is intentionally a simple proof-of-concept. It uses the existing
`ReceiptScanner` stub (no OCR) to produce deterministic results and keeps
state in memory.
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

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[3]

UPLOAD_DIR = REPO_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "dev-secret-key"

DOCS_DIR = REPO_ROOT / "docs" / "_build" / "html"

# In-memory store: id -> {filename, status, result}
STORE: Dict[str, Dict[str, Any]] = {}

# Add demo sample items (one good, one broken) for testing
sample_good_id = "sample-good"
sample_broken_id = "sample-broken"

STORE[sample_good_id] = {
    "filename": "sample_good.jpg",
    "status": "done",
    "result": {
        "merchant": "Sample Store",
        "date": "2026-03-14",
        "total": "23.45",
        "lines": ["Sample good receipt"],
    },
    "manual": False,
    "fixed": False,
    "path": str(UPLOAD_DIR / "sample_good.jpg"),
}

STORE[sample_broken_id] = {
    "filename": "sample_broken.jpg",
    "status": "done",
    "result": {
        "merchant": None,
        "date": None,
        "total": None,
        "lines": ["Broken OCR frame - missing fields"],
    },
    "manual": False,
    "fixed": False,
    "path": str(UPLOAD_DIR / "sample_broken.jpg"),
}


@app.route("/", methods=["GET"])
def index():
    records = receipts_dataframe(STORE)

    records_map = {str(r.get("id")): r for r in records}
    items = []

    for receipt_id, stored in STORE.items():
        meta = records_map.get(receipt_id, {})
        item = {"id": receipt_id, **stored}
        item["broken"] = bool(meta.get("broken", stored.get("result") is None))
        item["manual"] = bool(stored.get("manual", False))
        item["fixed"] = bool(stored.get("fixed", False))
        items.append(item)

    good_records = [r for r in records if not r.get("broken", False)]
    total_sum = sum(float(r.get("total") or 0.0) for r in good_records)
    count = len(good_records)

    summary = {
        "count": count,
        "total_sum": f"{total_sum:.2f}",
    }

    return render_template("index.html", items=items, summary=summary)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please choose a file to upload.")
        return redirect(url_for("index"))

    uid = str(uuid.uuid4())
    filename = Path(f.filename).name
    save_path = UPLOAD_DIR / f"{uid}_{filename}"
    f.save(save_path)

    STORE[uid] = {
        "filename": filename,
        "status": "processing",
        "result": None,
        "path": str(save_path),
        "manual": False,
        "fixed": False,
    }

    scanner = ReceiptScanner(
        use_ocr=False,
        image_processor=ImagePreprocessor(),
        ocr_processor=OCRProcessor(),
        text_processor=TextProcessor(),
    )

    try:
        res = scanner.parse_image(str(save_path))
        STORE[uid]["status"] = "done"
        STORE[uid]["result"] = res
    except Exception as exc:
        STORE[uid]["status"] = "error"
        STORE[uid]["result"] = {"error": str(exc)}

    return redirect(url_for("index"))


@app.route("/item/<id>")
def item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404
    return render_template("item.html", id=id, item=it)


@app.route("/item/<id>/save", methods=["POST"])
def save_item(id: str):
    it = STORE.get(id)
    if not it:
        return "Not found", 404

    merchant = (request.form.get("merchant") or "").strip()
    date = (request.form.get("date") or "").strip()
    total = (request.form.get("total") or "").strip()
    lines = (request.form.get("lines") or "").strip()

    if not (merchant and date and total):
        flash("Merchant, date and total are required to save/verify.")
        return redirect(url_for("item", id=id))

    it["result"] = {
        "merchant": merchant,
        "date": date,
        "total": total,
        "lines": [lines] if lines else [],
    }
    it["fixed"] = True
    it["manual"] = False
    it["status"] = "done"

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