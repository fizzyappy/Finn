"""Live run of the push engine on the demo portfolio -> backend/out/ + backend/push_report.md

    python -m finn.push.run
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .. import llm
from ..filings import IST, poll_rss
from . import alerts, digest, evaluate, portfolio

REPORT = Path(__file__).resolve().parents[2] / "push_report.md"


def _pct(x):
    return "–" if x is None else f"{x:.0%}"


def _card_lines(e: dict) -> list[str]:
    s = e.get("summary") or {}
    c = e.get("card") or {}
    L = [f"- **{e['symbol']}** · {e['category'].replace('_', ' ')} / {e['subtype'].replace('_', ' ')} · score "
         f"{e['score']} · {e['ts'][:16].replace('T', ' ')}",
         f"  - Headline: {s.get('headline')}  ", f"  - One line: {s.get('one_liner') or '–'} _(by {s.get('method')})_"]
    if c.get("type") == "results":
        L.append(f"  - Results card: **{c.get('status')}** ({c.get('period_type')}, {c.get('basis')}; "
                 f"pages {c.get('pages')}; model {c.get('model')})")
        bad = [x["name"] for x in c.get("checks", []) if not x["ok"]]
        L.append(f"    - Checks: {len(c.get('checks', [])) - len(bad)}/{len(c.get('checks', []))} passed"
                 + (f"; failed: {', '.join(bad)}" if bad else ""))
    if c.get("type") == "people":
        L.append(f"  - People card: **{c.get('status')}** - {c.get('headline')}")
        for p in c.get("people", [])[:2]:
            for b in p.get("background", [])[:1]:
                L.append(f"    - {p['name']}, p.{b['page']}: “{b['text'][:140]}”")
    L.append("  - Why: " + "; ".join(f"{p['why']} ({p['value']})" for p in e["score_parts"]))
    return L


def main(argv: list[str] | None = None) -> Path:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t0 = datetime.now(IST)
    rss = poll_rss()
    p = portfolio.load()
    ev = evaluate.run(use_llm=True)
    b7 = digest.build("7d", p=p)
    b14 = digest.build(((t0 - timedelta(days=14)).isoformat(), t0.isoformat()), p=p)
    series, _ = alerts.portfolio_series(p.symbols)
    bts = {name: alerts.backtest(name, series, days=90) for name in alerts.PRESETS}
    (digest.OUT_DIR / "backtests.json").write_text(json.dumps(bts, indent=1), encoding="utf-8")

    L = ["# FINN push engine: live run", "",
         f"Run {t0:%Y-%m-%d %H:%M} IST on this PC, demo portfolio of {len(p.symbols)} holdings. "
         "Everything below was produced live; the full output is in `backend/out/brief_7d.json` and `brief_custom.json` (14 days).", "",
         f"RSS poll: {rss}", ""]
    L += ["## 1. Classifier accuracy (hand-labelled real filings)", "",
          "| Set | Filings | Category correct | Treatment correct (hero / one-liner / collapsed) |", "|---|---|---|---|"]
    ps, hr, hl = ev["portfolio_set"], ev["heldout_rules_only"], ev["heldout_with_llm"]
    L.append(f"| Portfolio filings, rules + Gemini | {ps['n']} | {_pct(ps['category_accuracy'])} | {_pct(ps['treatment_accuracy'])} |")
    L.append(f"| Other companies (RSS), rules only | {hr['n']} | {_pct(hr['category_accuracy'])} | – |")
    L.append(f"| Other companies (RSS), rules + Gemini | {hl['n']} | {_pct(hl['category_accuracy'])} | – |")
    L += ["", "Honest caveat: the rules were written after seeing the portfolio set, and fixed after a first pass on the "
          "other-company set (first pass: rules alone 53%, rules + Gemini 82%). Both numbers above are therefore "
          "in-sample. Treatment confusion: " + ", ".join(f"{k}: {v}" for k, v in ps["treatment_confusion"].items()), ""]
    if ps["errors"]:
        L.append("Remaining disagreements with my labels:")
        L += [f"- {e['company']}: “{e['subject']}” labelled {e['want']}/{e.get('want_treatment')}, "
              f"engine says {e['got']}/{e.get('got_treatment')} (score {e.get('score')})" for e in ps["errors"]]
        L.append("")

    for title, b in (("2. Digest: last 7 days", b7), ("3. Digest: last 14 days (to show results season)", b14)):
        L += [f"## {title}", "", f"**{b['header']['text']}** · window {b['window']['from'][:16]} → {b['window']['to'][:16]}"
              + (f" · {b['quiet_message']}" if b["quiet"] else ""), ""]
        L.append("### Hero cards")
        for e in b["hero"]:
            L += _card_lines(e)
        L += ["", "### One-liners"]
        for e in b["one_liners"]:
            s = e.get("summary") or {}
            L.append(f"- **{e['symbol']}** ({e['score']}): {s.get('one_liner') or s.get('headline')}")
        L += ["", "### Collapsed", ", ".join(f"{k.replace('_', ' ')} {v['count']}" for k, v in b["collapsed"].items()) or "none", "",
              "### Price / volume alerts"]
        for a in b["alerts"][:8]:
            L.append(f"- {a['date']}: {a['text']} ({'; '.join(a['rules'])})")
            for fb in a["filed_before"]:
                L.append(f"  - Filed before this move: {fb['ts'][:16].replace('T', ' ')} {fb['title'][:90]}")
        if len(b["alerts"]) > 8:
            L.append(f"- … and {len(b['alerts']) - 8} more")
        u = b["llm_usage"]["models"]
        L += ["", f"Gemini use for this brief: " + ("; ".join(f"{m}: {v['api_calls']} calls, {v['cache_hits']} cache hits, "
              f"{v['tokens_in'] + v['tokens_out']:,} tokens" for m, v in u.items()) or "none (all cached)")
              + f" · cost {b['llm_usage']['pricing']}", f"Built in {b['data_status']['as_of']['built_in_seconds']} s. "
              f"{b['data_status']['filings_note'] or ''}", ""]

    L += ["## 4. Alert rules: 90-day backtest across the portfolio", "",
          "| Rule | Fires | Per week | Most frequent | Never fired |", "|---|---|---|---|---|"]
    for name, bt in bts.items():
        top = ", ".join(f"{k} {len(v)}" for k, v in list(bt["per_symbol"].items())[:3])
        L.append(f"| {bt['rule']['label']} | {bt['fires_total']} | {bt['fires_per_week']} | {top} | {len(bt['quiet_symbols'])} |")
    L += ["", "The preview changed the default. The obvious rule (a 2.5-sigma move) would fire about 1.2% of days if "
          "returns were bell-shaped, about 20 times here; real returns have fatter tails and it fired 58 times, ~3 a "
          "week: too noisy to be worth a push. The default is now 'notable move' (3 sigma after the market AND 2.5x "
          "normal volume), which fired about once a week. The investor can still pick any preset or a custom rule.", ""]
    def usage_line(u: dict) -> str:
        return "; ".join(f"{m}: {v['api_calls']} API calls, {v['cache_hits']} cache hits, {v['failed']} failed, "
                         f"{v['tokens_in']:,} in / {v['tokens_out']:,} out tokens" for m, v in u["models"].items()) \
            + f". Cost: {u['pricing']}."
    midnight = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    L += ["## 5. Cost", "", f"This run (answers mostly reused from the cache): {usage_line(llm.usage(since=t0.timestamp()))}", "",
          f"All Gemini use today, including the first time each filing was read: {usage_line(llm.usage(since=midnight.timestamp()))}",
          "", "Every model answer is cached by a hash of its exact input, so re-running a digest, or a second user "
          "holding the same stock, costs nothing.", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {REPORT}")
    return REPORT


if __name__ == "__main__":
    main()
