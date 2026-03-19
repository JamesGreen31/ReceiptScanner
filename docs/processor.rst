Processor Module
================

The `processor` module provides a small, stable frame for the receipt
parsing API consumed by the CLI and Flask UI.

API
---

.. automodule:: marymount.edu.receiptscanner.processor
   :members:
   :undoc-members:
   :show-inheritance:

Notes
-----

- `ReceiptScanner.parse_image(image_path)` returns a deterministic stub
  dict with fields: `merchant`, `date`, `total`, `lines`.
- `receipts_dataframe(store)` converts the in-memory `STORE` mapping to a
  list of normalized records used by the web UI.
