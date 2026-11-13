"""SQLite storage: a JSON cache with per-source freshness, plus tables for filings
and downloaded documents.

Why JSON, not pickle: readable with any SQLite viewer, safe to load, and it does
not break when a library (pandas) changes its internal format.

Why stale-on-error: exchanges and screener rate-limit and sometimes refuse. For an
investor, yesterday's numbers clearly marked "as of yesterday" beat an error screen.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    ns TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
    source TEXT, fetched_at REAL NOT NULL, PRIMARY KEY (ns, key));
CREATE TABLE IF NOT EXISTS filings (
    uid TEXT PRIMARY KEY, exchange TEXT, bse_code TEXT, symbol TEXT, company TEXT,
    ts TEXT, subject TEXT, detail TEXT, category TEXT, url TEXT, source TEXT,
    seen_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS filings_bse ON filings (bse_code, ts);
CREATE INDEX IF NOT EXISTS filings_sym ON filings (symbol, ts);
CREATE TABLE IF NOT EXISTS documents (
    url TEXT PRIMARY KEY, sha256 TEXT, path TEXT, bytes INTEGER, content_type TEXT,
    pages INTEGER, text_chars INTEGER, status TEXT, fetched_at REAL NOT NULL);
"""


@dataclass
class Fetched:
    """A value plus where it came from and how fresh it is."""
    data: Any
    source: str
    fetched_at: float
    stale: bool = False
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def as_of(self) -> str:
        return datetime.fromtimestamp(self.fetched_at, tz=timezone.utc).isoformat(timespec="seconds")

    def meta(self) -> dict:
        return {"source": self.source, "as_of": self.as_of, "stale": self.stale,
                "error": self.error, "notes": self.notes}


class Store:
    def __init__(self, path: Path | str = config.DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------------------------------------------------------------- cache
    def get(self, ns: str, key: str) -> tuple[Any, float, str] | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT value, fetched_at, source FROM cache WHERE ns=? AND key=?", (ns, key)
            ).fetchone()
        return (json.loads(row[0]), row[1], row[2]) if row else None

    def put(self, ns: str, key: str, value: Any, source: str = "") -> float:
        now = time.time()
        with self._lock:
            self.conn.execute(
                "REPLACE INTO cache (ns, key, value, source, fetched_at) VALUES (?,?,?,?,?)",
                (ns, key, json.dumps(value, default=str), source, now),
            )
            self.conn.commit()
        return now

    def cached(self, ns: str, key: str, fetch: Callable[[], tuple[Any, str]],
               ttl: float | None = None, refresh: bool = False) -> Fetched:
        """Return a fresh cached value, else call fetch() -> (data, source).
        If fetch fails and an older value exists, return it marked stale."""
        ttl = config.TTL.get(ns, 3600) if ttl is None else ttl
        hit = self.get(ns, key)
        if hit and not refresh and time.time() - hit[1] <= ttl:
            return Fetched(hit[0], hit[2] or "", hit[1])
        try:
            data, source = fetch()
        except Exception as e:  # noqa: BLE001 - any failure falls back to the stale copy
            if hit:
                return Fetched(hit[0], hit[2] or "", hit[1], stale=True,
                               error=f"{type(e).__name__}: {e}"[:300])
            raise
        ts = self.put(ns, key, data, source)
        return Fetched(data, source, ts)

    # ---------------------------------------------------------------- filings
    def upsert_filings(self, rows: list[dict]) -> int:
        cols = ("uid", "exchange", "bse_code", "symbol", "company", "ts", "subject",
                "detail", "category", "url", "source")
        now = time.time()
        new = 0
        with self._lock:
            for r in rows:
                cur = self.conn.execute(
                    f"INSERT OR IGNORE INTO filings ({','.join(cols)}, seen_at) "
                    f"VALUES ({','.join('?' * len(cols))}, ?)",
                    (*[r.get(c) for c in cols], now),
                )
                new += cur.rowcount
            self.conn.commit()
        return new

    def filings_for(self, *, bse_code: str | None, symbol: str | None, since_iso: str) -> list[dict]:
        clauses, args = [], []
        if bse_code:
            clauses.append("bse_code=?")
            args.append(bse_code)
        if symbol:
            clauses.append("symbol=?")
            args.append(symbol)
        if not clauses:
            return []
        q = f"SELECT * FROM filings WHERE ({' OR '.join(clauses)}) AND ts >= ? ORDER BY ts DESC"
        with self._lock:
            cur = self.conn.execute(q, (*args, since_iso))
            names = [d[0] for d in cur.description]
            return [dict(zip(names, row)) for row in cur.fetchall()]

    # ---------------------------------------------------------------- documents
    def get_document(self, url: str) -> dict | None:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM documents WHERE url=?", (url,))
            row = cur.fetchone()
            return dict(zip([d[0] for d in cur.description], row)) if row else None

    def put_document(self, rec: dict) -> None:
        cols = ("url", "sha256", "path", "bytes", "content_type", "pages", "text_chars", "status")
        with self._lock:
            self.conn.execute(
                f"REPLACE INTO documents ({','.join(cols)}, fetched_at) VALUES ({','.join('?' * len(cols))}, ?)",
                (*[rec.get(c) for c in cols], time.time()),
            )
            self.conn.commit()


_store: Store | None = None


def store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def use_store(s: Store) -> None:
    """Swap the global store (tests use a temporary database)."""
    global _store
    _store = s
