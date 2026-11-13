"""Turn whatever the user types into one canonical company record.

People type "reliance", "RELIANCE.NS", "500325", "M&M" or "hdfc bank". Each source
wants a different key (Yahoo: RELIANCE.NS, BSE: 500325, screener: RELIANCE).

The list of companies comes from NSE's own published file (EQUITY_L.csv: symbol,
name, ISIN, series), refreshed weekly. The BSE scrip code comes from the
company's screener page, which links to its BSE page. Works for any listed
company; nothing here is company-specific.
"""
from __future__ import annotations

import csv
import difflib
import io
import re
from dataclasses import asdict, dataclass

from . import http, screener
from .store import store

NSE_MASTER_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


@dataclass
class Instrument:
    symbol: str | None          # NSE symbol, e.g. RELIANCE (None if BSE-only)
    bse_code: str | None        # e.g. 500325
    name: str | None = None
    isin: str | None = None
    series: str | None = None
    screener_id: str | None = None

    @property
    def yahoo(self) -> str:
        return f"{self.symbol}.NS" if self.symbol else f"{self.bse_code}.BO"

    @property
    def yahoo_bse(self) -> str | None:
        return f"{self.bse_code}.BO" if self.bse_code else None

    @property
    def screener_key(self) -> str:
        return self.symbol or str(self.bse_code)

    def to_dict(self) -> dict:
        return {**asdict(self), "yahoo": self.yahoo}


def normalise(raw: str) -> str:
    t = raw.strip().upper()
    t = re.sub(r"\.(NS|BO|NSE|BSE)$", "", t)
    t = re.sub(r"^(NSE|BSE)\s*:\s*", "", t)
    return t


def parse_master(text: str) -> dict[str, dict]:
    rows = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    out = {}
    for r in rows:
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        sym = r.get("SYMBOL")
        if sym:
            out[sym] = {"name": r.get("NAME OF COMPANY"), "isin": r.get("ISIN NUMBER"),
                        "series": r.get("SERIES"), "listed": r.get("DATE OF LISTING")}
    return out


def nse_master(refresh: bool = False) -> dict[str, dict]:
    def fetch():
        text = http.get_text(NSE_MASTER_URL, timeout=60)
        master = parse_master(text)
        if len(master) < 500:
            raise http.SourceError(f"NSE master looks truncated ({len(master)} rows)")
        return master, "NSE EQUITY_L.csv"
    return store().cached("nse_master", "EQUITY_L", fetch, refresh=refresh).data


_SUFFIX = re.compile(r"\b(limited|ltd|the|india|co|company|corporation|corp|inc)\b\.?")


def _norm_name(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def search(text: str, limit: int = 8, master: dict | None = None) -> list[dict]:
    """Best matches by symbol or company name."""
    master = master if master is not None else nse_master()
    q = normalise(text)
    qn = _norm_name(text)
    scored = []
    for sym, info in master.items():
        name_n = _norm_name(info.get("name") or "")
        if sym == q:
            score = 1.0
        elif qn and name_n == qn:
            score = 0.98
        elif sym.startswith(q):
            score = 0.9 - 0.01 * (len(sym) - len(q))
        elif qn and qn in name_n:
            score = 0.85 - 0.002 * (len(name_n) - len(qn))
        else:
            score = difflib.SequenceMatcher(None, qn, name_n).ratio() * 0.8
        if score > 0.55:
            scored.append((score, sym, info))
    scored.sort(key=lambda x: -x[0])
    return [{"symbol": s, "score": round(sc, 3), **i} for sc, s, i in scored[:limit]]


def match_company_name(name: str, master: dict | None = None) -> str | None:
    """Exact-after-normalisation name match (used for NSE RSS items, which carry only names)."""
    master = master if master is not None else nse_master()
    target = _norm_name(name)
    for sym, info in master.items():
        if _norm_name(info.get("name") or "") == target:
            return sym
    return None


def _resolve(key: str) -> tuple[dict, str]:
    master = nse_master()
    symbol = bse = None
    if key.isdigit() and len(key) == 6:
        bse = key
    elif key in master:
        symbol = key
    else:
        hits = search(key, limit=5, master=master)
        if hits and hits[0]["score"] >= 0.85:
            symbol = hits[0]["symbol"]
        else:
            sugg = ", ".join(h["symbol"] for h in hits) or "none"
            raise LookupError(f"Unknown company '{key}'. Did you mean: {sugg}?")
    page = screener.company(symbol or bse)
    d = page.data
    bse = bse or d.get("bse_code")
    if not symbol and d.get("nse_symbol") in master:
        symbol = d["nse_symbol"]
    info = master.get(symbol or "", {})
    return {
        "symbol": symbol, "bse_code": bse, "name": info.get("name") or d.get("name"),
        "isin": info.get("isin"), "series": info.get("series"), "screener_id": d.get("company_id"),
    }, "NSE master + screener.in"


def resolve(raw: str, refresh: bool = False) -> Instrument:
    key = normalise(raw)
    rec = store().cached("instrument", key, lambda: _resolve(key), refresh=refresh)
    return Instrument(**rec.data)
