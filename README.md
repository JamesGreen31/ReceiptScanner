# ReceiptScanner
A simple POC for a receipt information extractor

## Install (development)

Create and activate a virtual environment, then install the package in editable mode with development extras:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[all]'
```

## Run

Run the console script after installation:

```powershell
receiptscanner
```

Or run the module directly (without installing):

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from marymount.edu.receiptscanner import main as m; m.main()"
```

## Tests

Run tests with:

```powershell
python -m pytest -q
```

## Development

Formatting and linting tools are available via the `dev` extras in `pyproject.toml`.

## Web POC

The project includes a minimal Flask-based proof-of-concept web UI for uploading receipts and viewing statuses. It uses the stubbed scanner (no OCR) so no additional system dependencies are required.

Install the web extra and run the web server:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e '.[web]'
python -m marymount.edu.receiptscanner.web
```

Then open `http://localhost:8000` in your browser. Uploaded files are saved to a local `uploads/` folder and processed synchronously with stub output.


