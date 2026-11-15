"""Recompute FINN's take for every cached research result and the app's built-in copies (no model calls).
Run: python -m finn.pull.retake"""
from __future__ import annotations

import json
from pathlib import Path

from ..store import store
from .. import fundamentals, symbols
from . import narrative, tables


def _bank(r: dict) -> None:
    if not (r["sections"].get("snapshot") or {}).get("lender"):
        return
    try:
        key = symbols.resolve(r["ticker"]).screener_key
        b = tables.bank(fundamentals.get_fundamentals(key).data)
        if b:
            r["sections"]["bank"] = b
    except Exception as e:  # noqa: BLE001
        print(r["ticker"], "bank numbers skipped:", type(e).__name__)

SNAP = Path(__file__).resolve().parents[3] / "frontend" / "public" / "data" / "research"


def main() -> None:
    n = 0
    for (k,) in store().conn.execute("SELECT key FROM cache WHERE ns='research'").fetchall():
        hit = store().get("research", k)
        if hit:
            r = hit[0]
            _bank(r)
            r["sections"]["take"] = narrative.finns_take(r["sections"])
            r["sections"]["chart_notes"] = narrative.chart_notes(r["sections"])
            store().put("research", k, r, "pull engine")
            n += 1
    for f in SNAP.glob("*.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        _bank(r)
        r["sections"]["take"] = narrative.finns_take(r["sections"])
        r["sections"]["chart_notes"] = narrative.chart_notes(r["sections"])
        f.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        n += 1
    print("updated", n)


if __name__ == "__main__":
    main()
