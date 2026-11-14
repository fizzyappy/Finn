"""Freeze real outputs into the app (frontend/public/data/) so the deployed link always
works without the backend. Everything is labelled with when it was produced.

    python -m finn.export_snapshot
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import config, llm, symbols
from .filings import IST
from .push import alerts, digest, portfolio
from .store import store

OUT = config.ROOT / "frontend" / "public" / "data"
RESEARCH_NAMES = ["ASIANPAINT", "TITAN", "HAL"]


def _write(name: str, obj) -> int:
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))
    p.write_text(txt, encoding="utf-8")
    return len(txt)


def _research_cached(ticker: str) -> dict | None:
    rows = store().conn.execute("SELECT key FROM cache WHERE ns='research' AND key LIKE ? ORDER BY fetched_at DESC",
                                (f"{ticker}|%",)).fetchall()
    for (k,) in rows:
        hit = store().get("research", k)
        if hit:
            return hit[0]
    return None


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    now = datetime.now(IST)
    p = portfolio.load()
    sizes = {}

    # Briefs for every window (cached model answers; no new spend for known filings).
    def usable(b: dict) -> bool:
        """At least half the holdings had a working filings source."""
        st = b["data_status"]["filings_sources"]
        ok = sum(1 for v in st.values() if isinstance(v, dict) and any(str(x).startswith("ok") for x in v.values()))
        return ok >= len(p.symbols) / 2

    windows = {"since_last_look": "24h", "24h": "24h", "3d": "3d", "7d": "7d"}
    b14 = digest.build(((now - timedelta(days=14)).isoformat(), now.isoformat()), p=p, save=False, now=now)
    if not usable(b14):
        raise SystemExit("filings sources failed for most holdings: keeping the previous snapshot")
    b14["window"]["label"] = "last 14 days"
    sizes["brief_14d"] = _write("brief_14d.json", b14)
    for name, w in windows.items():
        b = digest.build(w, p=p, save=False, now=now)
        if name == "since_last_look":
            b["window"]["label"] = "since you last looked"
        sizes[f"brief_{name}"] = _write(f"brief_{name}.json", b)

    # Research for the portfolio and the research names (from the research cache).
    index = []
    for tk in list(p.symbols) + RESEARCH_NAMES:
        r = _research_cached(tk)
        if not r:
            continue
        sizes[f"research_{tk}"] = _write(f"research/{tk}.json", r)
        rc = r["sections"].get("report_card") or {}
        index.append({"ticker": tk, "name": r.get("name"), "kept": rc.get("promises_kept"),
                      "dodged": rc.get("questions_dodged"), "as_of": r.get("started_at"),
                      "in_portfolio": tk in p.weights})
    sizes["research_index"] = _write("research_index.json", index)

    # Company list for search (NSE equity series), compact.
    master = symbols.nse_master()
    syms = [[s, i.get("name")] for s, i in master.items() if i.get("series") in ("EQ", "BE", "BZ", "SM", "ST")]
    sizes["symbols"] = _write("symbols.json", syms)

    # Per-day measures for the live backtest slider (last 120 trading days).
    series, price_status = alerts.portfolio_series(p.symbols)
    compact = {s: [[r["date"], r["ret_pct"], r.get("mkt_ret_pct"), r.get("z"), r.get("vol_x"), r["close"],
                    int(bool(r.get("provisional")))] for r in rows[-120:]] for s, rows in series.items()}
    # Never replace good data with a broken run (e.g. a cloud host refused by Yahoo).
    if len(compact) >= len(p.symbols) / 2:
        sizes["alert_series"] = _write("alert_series.json", {"fields": ["date", "ret_pct", "mkt_ret_pct", "z", "vol_x",
                                                                         "close", "provisional"], "series": compact})
    else:
        print(f"prices for only {len(compact)} of {len(p.symbols)} holdings: keeping the previous alert_series.json")

    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    usage_today = llm.usage(since=midnight.timestamp())
    usage_all = llm.usage(since=0)
    meta = {
        "generated_at": now.isoformat(timespec="seconds"),
        "portfolio": {"name": p.name, "holdings": [{"symbol": s, "weight": w} for s, w in p.weights.items()],
                      "preferences": p.preferences, "alert_rules": p.alert_rules},
        "presets": {k: v.__dict__ for k, v in alerts.PRESETS.items()},
        "llm_today": usage_today, "llm_all_time": usage_all,
        "prices": price_status,
        "filings_sources": b14["data_status"]["filings_sources"],
        "filings_note": b14["data_status"]["filings_note"],
        "research_names": RESEARCH_NAMES,
    }
    sizes["meta"] = _write("meta.json", meta)
    print(json.dumps({k: f"{v / 1024:.0f} KB" for k, v in sizes.items()}, indent=1))
    print(f"snapshot written to {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
