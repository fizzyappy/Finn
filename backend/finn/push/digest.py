"""The digest: everything across the portfolio in a time window, sorted by how
much it matters, with the routine collapsed. Output is brief.json for the app.

Windows: "since_last_look", "24h", "3d", "7d", or a custom (from, to).
Pipeline per filing: classify -> market reaction -> materiality (with reasons)
-> treatment. Same-company, same-category filings in the window become one event
(the most material one leads, the rest ride along). Hero events get a card
(results / people / summary), one-liners get a verified one-line summary, the
rest are counted per category. Price/volume alerts are added with the filings
made before each move.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta
from pathlib import Path

from .. import filings, fundamentals, llm
from ..filings import IST
from ..store import store
from . import alerts as alerts_mod
from . import classify, materiality, people, portfolio, results_card, summarize

WINDOWS = {"24h": timedelta(hours=24), "3d": timedelta(days=3), "7d": timedelta(days=7)}
OUT_DIR = Path(__file__).resolve().parents[2] / "out"


def _meta_get(key: str) -> str | None:
    conn = store().conn
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def _meta_set(key: str, value: str) -> None:
    conn = store().conn
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("REPLACE INTO meta VALUES (?, ?)", (key, value))
    conn.commit()


def resolve_window(window: str | tuple, now: datetime) -> tuple[datetime, datetime, str]:
    if isinstance(window, tuple):
        a, b = (datetime.fromisoformat(x) for x in window)
        a = a if a.tzinfo else a.replace(tzinfo=IST)
        b = b if b.tzinfo else b.replace(tzinfo=IST)
        return a, b, "custom"
    if window == "since_last_look":
        last = _meta_get("last_look")
        start = datetime.fromisoformat(last) if last else now - WINDOWS["24h"]
        return start, now, "since last look" if last else "last 24 hours (first look)"
    if window not in WINDOWS:
        raise ValueError(f"window must be one of {sorted(WINDOWS) + ['since_last_look']} or (from, to)")
    return now - WINDOWS[window], now, {"24h": "last 24 hours", "3d": "last 3 days", "7d": "last 7 days"}[window]


def reaction_for(f: dict, series: list[dict]) -> dict | None:
    """The stock's day: the filing day if filed before the 3:30 pm close, else the next trading day."""
    try:
        ts = datetime.fromisoformat(f["ts"]).astimezone(IST)
    except (TypeError, ValueError, KeyError):
        return None
    day = ts.date().isoformat()
    after_close = (ts.hour, ts.minute) >= (15, 30)
    for row in series:
        if row["date"] > day or (row["date"] == day and not after_close):
            return {"date": row["date"], "ret_pct": row["ret_pct"], "z": row.get("z") or 0.0, "vol_x": row.get("vol_x") or 0.0}
    return None


def cluster(items: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for it in items:
        key = (it["symbol"], it["category"]) if it["category"] != "unclassified" else (it["symbol"], it["uid"])
        groups.setdefault(key, []).append(it)
    events = []
    for g in groups.values():
        g.sort(key=lambda x: (-x["score"], x["ts"]))
        lead = dict(g[0])
        lead["related"] = [{"ts": x["ts"], "title": x["subject"], "url": x["url"], "treatment": x["treatment"]}
                           for x in g[1:]]
        events.append(lead)
    return events


def build(window: str | tuple = "24h", *, p: portfolio.Portfolio | None = None, use_llm: bool = True,
          mark_seen: bool = False, now: datetime | None = None, rules: list | None = None,
          save: bool = True) -> dict:
    t0 = time.time()
    now = now or datetime.now(IST)
    p = p or portfolio.load()
    start, end, window_label = resolve_window(window, now)
    days = max(1, math.ceil((end - start).total_seconds() / 86400))

    series, price_status = alerts_mod.portfolio_series(p.symbols)
    rule_objs = [alerts_mod.rule_from(r) for r in (rules or p.alert_rules or ["unusual_move", "volume_spike"])]

    raw, source_status, mcaps, trusted = [], {}, {}, {}
    for sym in p.symbols:
        try:
            res = filings.get_filings(sym, days=days + 1)
            source_status[sym] = res["status"]
            for f in res["items"]:
                if start.isoformat() <= (f.get("ts") or "") <= end.isoformat():
                    raw.append({**f, "symbol": sym})
        except Exception as e:  # noqa: BLE001
            source_status[sym] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
        try:
            fd = fundamentals.get_fundamentals(sym).data
            mcaps[sym] = (fd["top_ratios"].get("Market Cap", {}).get("values") or [None])[0]
            trusted[sym] = fundamentals.document_links(sym)
        except Exception:  # noqa: BLE001
            mcaps[sym], trusted[sym] = None, set()

    items = []
    for f in raw:
        c = classify.classify(f, use_llm=use_llm)
        react = reaction_for(f, series.get(f["symbol"], []))
        sc = materiality.score(f, c, weight=p.weights.get(f["symbol"]), mcap_cr=mcaps.get(f["symbol"]),
                               prefs=p.preferences, reaction=react)
        items.append({
            "uid": f.get("uid"), "symbol": f["symbol"], "company": f.get("company"), "ts": f.get("ts"),
            "subject": f.get("subject"), "url": f.get("url"), "sources": f.get("sources"),
            "category": c.category, "subtype": c.subtype, "class_method": c.method, "class_confidence": c.confidence,
            "card_kind": c.card, "reaction": react, **sc.to_dict(),
        })

    events = cluster(items)
    for e in events:
        tr = set(trusted.get(e["symbol"], set()))
        f = {"subject": e["subject"], "url": e["url"], "company": e["company"], "symbol": e["symbol"]}
        if e["treatment"] == "hero" and use_llm:
            e["summary"] = None
            if e["card_kind"] == "results" and e["url"]:
                e["card"] = results_card.build(e["url"], symbol=e["symbol"], trusted=tr)
                e["summary"] = results_card.summary(e["card"], e["symbol"])
            elif e["card_kind"] == "people" and e["url"]:
                e["card"] = people.build(e["url"], trusted=tr)
                e["card"]["headline"] = people.headline(e["card"])
            e["summary"] = e["summary"] or summarize.summarize(f, trusted=tr, category=e["category"])
        elif e["treatment"] == "one_liner":
            e["summary"] = summarize.summarize(f, trusted=tr, category=e["category"]) if use_llm else \
                {"headline": summarize.clean_subject(e["subject"] or ""), "one_liner": None, "method": "subject"}

    hero = sorted([e for e in events if e["treatment"] == "hero"], key=lambda e: -e["score"])
    one = sorted([e for e in events if e["treatment"] == "one_liner"], key=lambda e: -e["score"])
    collapsed: dict[str, dict] = {}
    for e in events:
        if e["treatment"] == "collapsed":
            c = collapsed.setdefault(e["category"], {"count": 0, "items": []})
            c["count"] += 1 + len(e["related"])
            c["items"].append({"symbol": e["symbol"], "ts": e["ts"], "title": e["subject"], "url": e["url"]})

    window_dates = {r["date"] for rows in series.values() for r in rows
                    if start.date().isoformat() <= r["date"] <= end.date().isoformat()}
    fired = alerts_mod.fired(series, rule_objs, window_dates)
    by_sym: dict[str, list[dict]] = {}
    for it in items:
        by_sym.setdefault(it["symbol"], []).append(it)
    merged_alerts: dict[tuple, dict] = {}
    for a in fired:
        k = (a["symbol"], a["date"])
        if k in merged_alerts:
            merged_alerts[k]["rules"].append(a["rule_label"])
            continue
        linked = alerts_mod.link_filings(a, by_sym)
        merged_alerts[k] = {"symbol": a["symbol"], "date": a["date"], "text": a["text"], "rules": [a["rule_label"]],
                            "measures": {x: a["measures"][x] for x in ("ret_pct", "mkt_ret_pct", "z", "vol_x", "beta",
                                                                       "sigma_pct", "provisional")},
                            "filed_before": [x for x in linked if x["treatment"] != "collapsed"],
                            "routine_filed_before": sum(1 for x in linked if x["treatment"] == "collapsed"),
                            "link_note": "Filings made before this move. Timing only: FINN does not claim they caused it."}
    alert_list = sorted(merged_alerts.values(), key=lambda a: (a["date"], abs(a["measures"]["z"] or 0)), reverse=True)

    n_filings = len(items)
    n_matter = len(hero) + len(one)
    quiet = not hero and not alert_list
    blocked = sorted({src for st in source_status.values() if isinstance(st, dict)
                      for src, v in st.items() if isinstance(v, str) and v.startswith("blocked")})
    brief = {
        "generated_at": now.isoformat(timespec="seconds"),
        "window": {"label": window_label, "from": start.isoformat(timespec="seconds"),
                   "to": end.isoformat(timespec="seconds")},
        "header": {
            "filings": n_filings, "events": len(events), "matter": n_matter, "hero": len(hero),
            "alerts": len(alert_list),
            "text": f"{n_filings} filing{'s' * (n_filings != 1)}, {n_matter} matter"
                    + (f" · {len(alert_list)} price/volume alert{'s' * (len(alert_list) != 1)}" if alert_list else ""),
        },
        "quiet": quiet,
        "quiet_message": (f"Quiet {window_label}: nothing material across your {len(p.symbols)} holdings"
                          + (f"; {n_filings} routine filing{'s' * (n_filings != 1)} collapsed." if n_filings else ".")) if quiet else None,
        "hero": hero, "one_liners": one,
        "collapsed": dict(sorted(collapsed.items(), key=lambda kv: -kv[1]["count"])),
        "alerts": alert_list,
        "alert_rules": [r.__dict__ for r in rule_objs],
        "data_status": {
            "prices": {s: v for s, v in price_status.items()},
            "filings_sources": source_status,
            "filings_note": None if not blocked else
                f"Sources refused on this connection: {', '.join(blocked)}. Filings come from screener's recent list "
                "and the BSE/NSE RSS store, so older or very busy days may be incomplete.",
            "as_of": {"prices_last_date": max((v.get("last_date") or "" for v in price_status.values()), default=None),
                      "built_in_seconds": round(time.time() - t0, 1)},
        },
        "llm_usage": llm.usage(since=t0),
        "holdings": [{"symbol": s, "weight": w} for s, w in p.weights.items()],
        "quiet_holdings": sorted(set(p.symbols) - {e["symbol"] for e in hero + one} - {a["symbol"] for a in alert_list}),
    }
    if mark_seen:
        _meta_set("last_look", end.isoformat())
    if save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        name = window if isinstance(window, str) else "custom"
        (OUT_DIR / f"brief_{name}.json").write_text(json.dumps(brief, indent=1, ensure_ascii=False, default=str),
                                                     encoding="utf-8")
    return brief
