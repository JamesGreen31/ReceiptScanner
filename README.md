# ReceiptScanner

ReceiptScanner is a Python-based proof-of-concept for extracting structured data from receipt images.

It provides:

- A Flask web application for uploading and reviewing receipts
- A CLI interface for running the processing pipeline
- Optional OCR-backed extraction using Tesseract
- A modular architecture for experimentation and extension

This project is intentionally a prototype, not a production system.

---

## Features

- Upload receipt images via web UI
- Extract key fields:
  - Merchant
  - Date
  - Total
  - Gallons
  - Price per gallon
- View OCR output
- Manually correct extracted values
- Organize receipts into collections
- View summary statistics
- Run with or without OCR

---

## Installation

Clone the repository:

    git clone https://github.com/JamesGreen31/ReceiptScanner.git
    cd ReceiptScanner

Create a virtual environment:

    python -m venv venv

Activate environment:

Windows:

    venv\Scripts\activate

macOS/Linux:

    source venv/bin/activate

Install dependencies:

    pip install -e ".[all]"

---

## Running the Application

### Web App

    python -m marymount.edu.receiptscanner.web

Open in browser:

    http://localhost:8000

### CLI

    receiptscanner

---

## OCR Setup

OCR requires Tesseract installed on your system.

Disable OCR if needed:

    USE_OCR = False

---

## Docker

### Build

    docker build -t receiptscanner .

### Run

    docker run -p 8000:8000 receiptscanner

### Example Dockerfile

    FROM python:3.11-slim

    RUN apt-get update && \
        apt-get install -y tesseract-ocr && \
        rm -rf /var/lib/apt/lists/*

    WORKDIR /app
    COPY . .

    RUN pip install --upgrade pip && \
        pip install -e ".[all]"

    CMD ["python", "-m", "marymount.edu.receiptscanner.web"]

---

## Project Structure

    src/marymount/edu/receiptscanner/
    ├── main.py
    ├── processor.py
    ├── service.py
    ├── web.py

---

## Limitations

- OCR accuracy varies based on image quality
- Rule-based parsing (not ML-based)
- No persistent storage (in-memory only)
- Not production hardened

---

## License

MIT License
