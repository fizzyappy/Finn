"""Live research run -> backend/out/research_<TICKER>.json + backend/research_report.md

    python -m finn.pull.run [TICKERS...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .. import llm
from . import engine

DEFAULT = ["INFY", "LT", "HDFCBANK", "ASIANPAINT", "TITAN", "HAL"]
OUT = Path(__file__).resolve().parents[2] / "out"
REPORT = Path(__file__).resolve().parents[2] / "research_report.md"


def _company(r: dict) -> list[str]:
    S = r["sections"]
    snap, cq, bs = S["snapshot"], S["cash_quality"], S["balance_sheet"]
    L = [f"## {r['name']} ({r['ticker']})", "",
         f"Built in {r.get('built_in_seconds')} s{' (from cache)' if r.get('from_cache') else ''}. "
         f"Transcripts read: {', '.join(t['call'] for t in r.get('transcripts', [])) or 'none'}."
         + (f" States: {'; '.join(s['message'] for s in r['states'])}" if r["states"] else ""), ""]
    lat = snap.get("latest") or {}
    L.append(f"- **Snapshot:** market cap Rs {snap.get('market_cap_cr') or 0:,.0f} cr, P/E {snap.get('pe')}, "
             f"latest quarter {snap.get('latest_quarter')}: revenue Rs {lat.get('revenue') or 0:,.0f} cr, profit Rs {lat.get('pat') or 0:,.0f} cr")
    c5 = (S["trajectory"].get("cagr_pct") or {}).get("5y") or {}
    L.append(f"- **5-year CAGR:** revenue {c5.get('revenue')}%, profit {c5.get('pat')}%")
    L.append(f"- **Balance sheet:** " + (bs.get("note") or f"debt/equity {bs.get('debt_to_equity')}, cash conversion cycle "
                                              f"{(bs.get('working_capital') or {}).get('ccc_days')} days"))
    L.append(f"- **Cash quality:** {cq.get('reading') or cq.get('note')}")
    b = S.get("business_snapshot") or {}
    segs = ", ".join(f"{s['name']} {s['mix_pct']}%" for s in b.get("segments", [])[:5])
    L.append(f"- **Segments ({b.get('status')}):** {segs or b.get('note')}" + (f" — {b['check']}" if b.get("check") else ""))
    rc = S.get("report_card") or {}
    L.append(f"- **Report card:** promises kept {rc.get('promises_kept', '–')}; questions dodged {rc.get('questions_dodged', '–')} "
             f"(partly answered {rc.get('questions_partly_answered', '–')}); topics dropped: {', '.join(rc.get('topics_dropped') or []) or 'none'}")
    led = S.get("promise_ledger")
    if led:
        L += ["", "| Verdict | Metric | Period | Target | Said | Reason |", "|---|---|---|---|---|---|"]
        for p in led["promises"]:
            if p["verdict"] == "Not measurable":
                continue
            s = p["said"]
            L.append(f"| {p['verdict']} | {p['metric'].replace('_', ' ')}{'' if p['scope'] in ('company', '') else ' (' + p['scope'] + ')'} | "
                     f"{p['horizon']} | {p['target']} | {s['call_date'][:7]}, p.{s['page']} | {p['reason'][:110]} |")
        nm = led["counts"]["Not measurable"]
        if nm:
            L.append(f"\n_{nm} more statements are tracked but not measurable from the tables (order inflow, constant "
                     "currency, segment-level, no date)._")
    nv = S.get("narrative_vs_numbers") or []
    if nv:
        L += ["", "**Narrative vs numbers:**"] + [f"- “{x['quote'][:200]}” ({x['speaker']}, p.{x['page']}) vs {x['numbers']}" for x in nv]
    bb = S.get("bull_bear") or {}
    if bb.get("bull") or bb.get("bear"):
        L += ["", "**Bull:**"] + [f"- {x['text']}" for x in bb["bull"]] + ["", "**Bear:**"] + [f"- {x['text']}" for x in bb["bear"]]
        if bb.get("removed"):
            L.append(f"\n_{len(bb['removed'])} bullet(s) removed for not standing on a fact._")
    dod = [j for d in S.get("dodged_questions") or [] for j in d.get("judged", []) if j["label"] == "dodged"]
    if dod:
        L += ["", "**Dodged questions:**"] + [f"- {j['analyst']}: “{j['question_quote'][:150]}” → “{j['answer_quote'][:150]}” "
                                              f"(p.{j['answer_page']}). {j['reason']}" for j in dod[:3]]
    L.append("")
    return L


def main(tickers: list[str] | None = None, refresh: bool = False) -> Path:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tickers = tickers or DEFAULT
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    results = []
    for tk in tickers:
        print(f"== {tk}", flush=True)
        try:
            r = engine.research(tk, refresh=refresh, progress=lambda s, o: print(f"   {s}", flush=True))
        except Exception as e:  # noqa: BLE001
            print(f"   FAILED: {type(e).__name__}: {e}")
            continue
        (OUT / f"research_{tk}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        results.append(r)
    L = ["# FINN pull engine: live research run", "",
         f"{len(results)} companies, run on this PC. Every number comes from the statement tables or the filings; every "
         "quote was found word for word on the page cited. Full output: `backend/out/research_<TICKER>.json`.", ""]
    for r in results:
        L += _company(r)
    u = llm.usage(since=t0)
    L += ["## Cost of this run", "", "; ".join(f"{m}: {v['api_calls']} calls, {v['cache_hits']} cache hits, {v['failed']} failed, "
          f"{v['tokens_in'] + v['tokens_out']:,} tokens" for m, v in u["models"].items()) + f". {u['pricing']}.", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {REPORT}")
    return REPORT


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--refresh"]
    main(args or None, refresh="--refresh" in sys.argv)
