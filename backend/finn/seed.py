"""A small seed so a fresh server (Render, GitHub Actions) does not redo paid or slow
work: every cached model answer (keyed by a hash of its exact input), finished research,
and company resolutions. PDFs and web pages are not included; they are re-fetched.

    python -m finn.seed export      # writes backend/seed/seed.jsonl.gz
    python -m finn.seed load        # merges it into the local SQLite cache
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

from . import llm
from .store import store

SEED = Path(__file__).resolve().parents[1] / "seed" / "seed.jsonl.gz"
CACHE_NS = ("research", "instrument")


def export(path: Path = SEED) -> dict:
    conn = store().conn
    conn.executescript(llm.SCHEMA_SQL)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = {"llm": 0, "cache": 0}
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in conn.execute("SELECT key, task, model, text, tokens_in, tokens_out, created FROM llm_cache"):
            fh.write(json.dumps({"t": "llm", "r": row}, ensure_ascii=False) + "\n")
            n["llm"] += 1
        for ns in CACHE_NS:
            for row in conn.execute("SELECT ns, key, value, source, fetched_at FROM cache WHERE ns=?", (ns,)):
                fh.write(json.dumps({"t": "cache", "r": row}, ensure_ascii=False) + "\n")
                n["cache"] += 1
    return {**n, "path": str(path), "kb": path.stat().st_size // 1024}


def load(path: Path = SEED) -> dict:
    if not path.exists():
        return {"loaded": 0, "note": "no seed file"}
    conn = store().conn
    conn.executescript(llm.SCHEMA_SQL)
    n = {"llm": 0, "cache": 0}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["t"] == "llm":
                conn.execute("INSERT OR IGNORE INTO llm_cache VALUES (?,?,?,?,?,?,?)", rec["r"])
                n["llm"] += 1
            else:
                conn.execute("INSERT OR IGNORE INTO cache (ns, key, value, source, fetched_at) VALUES (?,?,?,?,?)", rec["r"])
                n["cache"] += 1
    conn.commit()
    return n


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    print(export() if cmd == "export" else load())
