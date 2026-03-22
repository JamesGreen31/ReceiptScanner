"""
 Service.py 

 Simple application service layer for receipts.
 
 Authors: James Green, Chris Duckers, Numi Tesfay
 Supervised by: Dr. Natalia Bell
 Marymount University, Spring 2024
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import uuid


class ReceiptService:
    """Simple application service layer for receipts.

    Provides a small, testable API over the in-memory store used by the
    Flask app. Persistence is intentionally simple (in-memory) to keep
    this POC focused and easily testable.
    """

    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.store: Dict[str, Dict[str, Any]] = {}

    def add_receipt(self, path: Path, filename: str, collection: Optional[str] = None) -> str:
        uid = str(uuid.uuid4())
        self.store[uid] = {
            "filename": filename,
            "status": "processing",
            "result": None,
            "path": str(path),
            "manual": False,
            "fixed": False,
            "collection": collection,
        }
        return uid

    def set_result(self, uid: str, result: Dict[str, Any], status: str = "done") -> None:
        if uid not in self.store:
            raise KeyError(uid)
        normalized = self._normalize_result(result)
        self.store[uid]["result"] = normalized
        self.store[uid]["status"] = status

    def _to_float(self, value: object) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(str(value))
        except Exception:
            return None

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Do not attempt to normalize error payloads
        if not isinstance(result, dict) or result.get("error"):
            return result

        out = dict(result)
        out["gallons"] = self._to_float(out.get("gallons")) if out.get("gallons") is not None else None
        out["price_per_gallon"] = self._to_float(out.get("price_per_gallon")) if out.get("price_per_gallon") is not None else None
        # Preserve source flags but coerce to simple strings or None
        out["gallons_source"] = str(out.get("gallons_source")) if out.get("gallons_source") is not None else None
        out["price_per_gallon_source"] = str(out.get("price_per_gallon_source")) if out.get("price_per_gallon_source") is not None else None
        return out

    def mark_fixed(self, uid: str) -> None:
        if uid in self.store:
            self.store[uid]["fixed"] = True

    def get(self, uid: str) -> Optional[Dict[str, Any]]:
        return self.store.get(uid)

    def list(self, collection: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
        items = list(self.store.items())
        if collection is None:
            return items
        return [(k, v) for k, v in items if v.get("collection") == collection]

    def clear(self) -> None:
        self.store.clear()

    def summaries(self) -> Dict[str, Any]:
        """Return basic overall summaries (count, total_sum).

        This intentionally mirrors the shape used by the web UI so integrating
        it is straightforward.
        """
        good_total = 0.0
        count = 0
        gallons = 0.0
        for v in self.store.values():
            res = v.get("result") or {}
            try:
                t = float(str(res.get("total") or 0).replace(",", ""))
                g = float(str(res.get("gallons") or 0).replace(",", ""))
            except Exception:
                t = 0.0
                g = 0.0
            if t > 0:
                good_total += t
                count += 1
                gallons += g

        return {"count": count, "total_sum": f"{good_total:.2f} ", "total_gallons": f"{gallons:.2f}"}