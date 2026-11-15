"""Recompute FINN's take for every cached research result and the app's built-in copies (no model calls).
Run: python -m finn.pull.retake"""
from __future__ import annotations

import json
from pathlib import Path

from ..store import store
from . import narrative

SNAP = Path(__file__).resolve().parents[3] / "frontend" / "public" / "data" / "research"


def main() -> None:
    n = 0
    for (k,) in store().conn.execute("SELECT key FROM cache WHERE ns='research'").fetchall():
        hit = store().get("research", k)
        if hit:
            r = hit[0]
            r["sections"]["take"] = narrative.finns_take(r["sections"])
            store().put("research", k, r, "pull engine")
            n += 1
    for f in SNAP.glob("*.json"):
        r = json.loads(f.read_text(encoding="utf-8"))
        r["sections"]["take"] = narrative.finns_take(r["sections"])
        f.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        n += 1
    print("updated", n)


if __name__ == "__main__":
    main()
