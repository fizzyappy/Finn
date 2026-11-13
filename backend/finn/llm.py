"""The one place FINN talks to an LLM (Google Gemini).

- Tiers, not model names, in the calling code: "lite" for bulk work, "flash" for
  the second attempt when a lite answer fails its checks. Each tier has a
  fallback chain; an answer from a fallback model is labelled as such.
- Every call is cached by a hash of (task, tier, system, prompt, attached PDF,
  schema). The same filing processed twice costs nothing the second time.
- Every call (cached or not) is logged with tokens and latency; `usage()` feeds
  the in-app cost meter.
- Retries with backoff on rate limits / server errors, then the next model.
- No key, or FINN_OFFLINE=1: `available` is False and complete() returns None.
  Every caller has a deterministic fallback, so the app still works.
- The LLM never does arithmetic for us: callers ask it to *read* numbers;
  Python computes everything.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from . import config
from .store import store

TIERS: dict[str, list[str]] = {
    "lite": ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
    "flash": ["gemini-3.5-flash", "gemini-3.5-flash-lite"],
}
# USD per 1M tokens (input, output). Free tier = 0. Set real prices here if the
# key moves to a paid plan; the cost meter multiplies tokens by these.
PRICES: dict[str, tuple[float, float]] = {}
MIN_GAP_SECONDS = {"lite": 4.0, "flash": 6.0}   # stay under free-tier requests/minute

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, task TEXT, model TEXT, text TEXT,
    tokens_in INTEGER, tokens_out INTEGER, created REAL);
CREATE TABLE IF NOT EXISTS llm_log (ts REAL, task TEXT, tier TEXT, model TEXT, cached INTEGER, ok INTEGER,
    fallback INTEGER, tokens_in INTEGER, tokens_out INTEGER, latency REAL, error TEXT);
"""


@dataclass
class LLMResult:
    text: str
    model: str
    cached: bool
    fallback: bool
    tokens_in: int = 0
    tokens_out: int = 0
    data: Any = None                  # parsed JSON when a schema was given
    notes: list[str] = field(default_factory=list)


def _api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = config.ROOT / ".env"
    if env.exists():
        try:
            from dotenv import dotenv_values

            return dotenv_values(env).get("GEMINI_API_KEY") or None
        except Exception:  # noqa: BLE001
            return None
    return None


class Router:
    def __init__(self, client: Any = None):
        self._lock = threading.Lock()
        self._last_call: dict[str, float] = {}
        self._client = client
        self._schema_ready = False
        if client is None and os.environ.get("FINN_OFFLINE") != "1":
            key = _api_key()
            if key:
                from google import genai
                from google.genai import types

                self._client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=120_000))

    @property
    def available(self) -> bool:
        return self._client is not None

    # ---------------------------------------------------------------- storage
    def _db(self):
        conn = store().conn
        if not self._schema_ready:
            conn.executescript(SCHEMA_SQL)
            self._schema_ready = True
        return conn

    def _log(self, **kw) -> None:
        with self._lock:
            self._db().execute(
                "INSERT INTO llm_log VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), kw["task"], kw["tier"], kw.get("model"), int(kw.get("cached", 0)), int(kw.get("ok", 1)),
                 int(kw.get("fallback", 0)), kw.get("tokens_in", 0), kw.get("tokens_out", 0),
                 kw.get("latency", 0.0), kw.get("error")),
            )
            self._db().commit()

    @staticmethod
    def cache_key(task: str, tier: str, system: str, prompt: str, pdf: bytes | None, schema: dict | None) -> str:
        h = hashlib.sha256()
        for part in (task, tier, system, prompt, json.dumps(schema, sort_keys=True) if schema else ""):
            h.update(part.encode("utf-8"))
            h.update(b"\x00")
        if pdf:
            h.update(hashlib.sha256(pdf).digest())
        return h.hexdigest()

    # ---------------------------------------------------------------- calls
    def _pace(self, tier: str) -> None:
        gap = MIN_GAP_SECONDS.get(tier, 4.0)
        with self._lock:
            now = time.time()
            slot = max(now, self._last_call.get(tier, 0.0) + gap)
            self._last_call[tier] = slot
        if slot > now:
            time.sleep(slot - now)

    def _call_model(self, model: str, system: str, prompt: str, pdf: bytes | None,
                    schema: dict | None, max_tokens: int):
        from google.genai import types

        parts: list[Any] = []
        if pdf:
            parts.append(types.Part.from_bytes(data=pdf, mime_type="application/pdf"))
        parts.append(prompt)
        cfg = types.GenerateContentConfig(system_instruction=system or None, temperature=0,
                                          max_output_tokens=max_tokens)
        if schema:
            cfg.response_mime_type = "application/json"
            cfg.response_json_schema = schema
        return self._client.models.generate_content(model=model, contents=parts, config=cfg)

    def complete(self, task: str, prompt: str, *, system: str = "", tier: str = "lite",
                 schema: dict | None = None, pdf: bytes | None = None, max_tokens: int = 2048,
                 refresh: bool = False) -> LLMResult | None:
        key = self.cache_key(task, tier, system, prompt, pdf, schema)
        if not refresh:
            with self._lock:
                row = self._db().execute(
                    "SELECT text, model, tokens_in, tokens_out FROM llm_cache WHERE key=?", (key,)).fetchone()
            if row:
                self._log(task=task, tier=tier, model=row[1], cached=1)
                res = LLMResult(row[0], row[1], True, row[1] != TIERS[tier][0], row[2], row[3])
                res.data = _parse_json(row[0]) if schema else None
                return res
        if not self.available:
            return None

        errors = []
        for i, model in enumerate(TIERS[tier]):
            for attempt in range(3):
                self._pace(tier)
                t0 = time.time()
                try:
                    r = self._call_model(model, system, prompt, pdf, schema, max_tokens)
                    text = (r.text or "").strip()
                    u = getattr(r, "usage_metadata", None)
                    tin = int(getattr(u, "prompt_token_count", 0) or 0)
                    tout = int(getattr(u, "candidates_token_count", 0) or 0) + int(getattr(u, "thoughts_token_count", 0) or 0)
                    data = _parse_json(text) if schema else None
                    if not text or (schema and data is None):
                        raise ValueError("empty or non-JSON answer")
                    self._log(task=task, tier=tier, model=model, fallback=i > 0, tokens_in=tin,
                              tokens_out=tout, latency=time.time() - t0)
                    with self._lock:
                        self._db().execute("REPLACE INTO llm_cache VALUES (?,?,?,?,?,?,?)",
                                           (key, task, model, text, tin, tout, time.time()))
                        self._db().commit()
                    res = LLMResult(text, model, False, i > 0, tin, tout, data)
                    if i > 0:
                        res.notes.append(f"answered by fallback model {model}")
                    return res
                except Exception as e:  # noqa: BLE001
                    msg = f"{model}: {type(e).__name__}: {str(e)[:160]}"
                    errors.append(msg)
                    self._log(task=task, tier=tier, model=model, ok=0, latency=time.time() - t0, error=msg)
                    transient = any(s in str(e) for s in ("429", "500", "503", "504", "RESOURCE_EXHAUSTED",
                                                          "UNAVAILABLE", "DEADLINE"))
                    if not transient:
                        break
                    time.sleep(2 ** attempt * 3)
        return None


def _parse_json(text: str):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        s, e = text.find("{"), text.rfind("}")
        if 0 <= s < e:
            try:
                return json.loads(text[s:e + 1])
            except ValueError:
                return None
    return None


def usage(since: float = 0.0) -> dict:
    """Totals for the cost meter: calls, cache hits, tokens and cost per model."""
    conn = store().conn
    conn.executescript(SCHEMA_SQL)
    rows = conn.execute(
        "SELECT model, SUM(cached), SUM(1-cached), SUM(ok=0), SUM(tokens_in), SUM(tokens_out) "
        "FROM llm_log WHERE ts >= ? GROUP BY model", (since,)).fetchall()
    per_model, total_cost = {}, 0.0
    for model, hits, calls, fails, tin, tout in rows:
        pin, pout = PRICES.get(model or "", (0.0, 0.0))
        cost = ((tin or 0) * pin + (tout or 0) * pout) / 1e6
        total_cost += cost
        per_model[model or "?"] = {"api_calls": calls or 0, "cache_hits": hits or 0, "failed": fails or 0,
                                   "tokens_in": tin or 0, "tokens_out": tout or 0, "cost_usd": round(cost, 4)}
    return {"models": per_model, "cost_usd": round(total_cost, 4),
            "pricing": "free tier (USD 0)" if not PRICES else "PRICES table"}


_router: Router | None = None


def router() -> Router:
    global _router
    if _router is None:
        _router = Router()
    return _router


def use_router(r: Router | None) -> None:
    global _router
    _router = r
