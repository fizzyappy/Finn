"""Narrative vs numbers, and bull vs bear. Every line must stand on a number from the
tables or a verified quote, or it is removed.

- Fact pool: numbered facts computed by Python (growth, margins, debt, cash quality,
  promise verdicts, dodged questions), each with its source.
- Narrative vs numbers (no LLM): where management, in the latest call, describes a
  metric as improving or strong, and the latest quarter's numbers moved the other
  way. The quote is verified on its page; the numbers come from the tables.
- Bull vs bear: Gemini Flash-Lite picks and phrases 3 bullets each from the fact
  pool, citing fact ids. Python keeps a bullet only if it cites real facts, every
  number in it appears in those facts, and it has no unsupported praise words.
"""
from __future__ import annotations

import re

from .. import documents, llm
from ..push.summarize import unsupported_adjectives
from .promises import sentences
from .transcripts import Transcript


def fact_pool(tables: dict, ledger: dict | None, dodged: list[dict] | None) -> list[dict]:
    facts: list[dict] = []

    def add(text: str, source: str):
        facts.append({"id": f"F{len(facts) + 1}", "text": text, "source": source})
    snap, traj, bs, cq = tables["snapshot"], tables["trajectory"], tables["balance_sheet"], tables["cash_quality"]
    lat = snap.get("latest") or {}
    if snap.get("pe"):
        add(f"P/E {snap['pe']:g}, market cap Rs {snap['market_cap_cr']:,.0f} cr", "screener ratios")
    for n in ("3y", "5y"):
        c = (traj.get("cagr_pct") or {}).get(n) or {}
        if c.get("revenue") is not None:
            add(f"{n} revenue CAGR {c['revenue']}%, profit CAGR {c.get('pat')}%", "annual P&L")
    q = traj.get("quarters") or []
    if len(q) >= 5 and q[-1].get("revenue") and q[-5].get("revenue"):
        g = round((q[-1]["revenue"] / q[-5]["revenue"] - 1) * 100, 1)
        add(f"Latest quarter ({q[-1]['quarter_end']}) revenue Rs {q[-1]['revenue']:,.0f} cr, {g:+.1f}% YoY", "quarterly P&L")
        if q[-1].get("pat") and q[-5].get("pat") and q[-5]["pat"] > 0:
            g2 = round((q[-1]["pat"] / q[-5]["pat"] - 1) * 100, 1)
            add(f"Latest quarter profit Rs {q[-1]['pat']:,.0f} cr, {g2:+.1f}% YoY", "quarterly P&L")
        if q[-1].get("ebitda_margin_pct") is not None and q[-5].get("ebitda_margin_pct") is not None:
            d = round(q[-1]["ebitda_margin_pct"] - q[-5]["ebitda_margin_pct"], 1)
            add(f"Operating margin {q[-1]['ebitda_margin_pct']}% in the latest quarter, {d:+.1f} pts YoY", "quarterly P&L")
    if lat.get("gross_npa_pct") is not None:
        add(f"Gross NPA {lat['gross_npa_pct']}%, net NPA {lat.get('net_npa_pct')}%", "quarterly results")
    if bs.get("debt_to_equity") is not None:
        add(f"Debt/equity {bs['debt_to_equity']} (borrowings Rs {bs['borrowings']:,.0f} cr)", "balance sheet")
    wc = bs.get("working_capital") or {}
    if wc.get("ccc_days") is not None:
        add(f"Cash conversion cycle {wc['ccc_days']:g} days ({wc['year_end'][:4]})", "ratios")
    if bs.get("deposit_growth_pct") is not None:
        add(f"Deposits grew {bs['deposit_growth_pct']}% in the latest year", "balance sheet")
    if cq.get("three_year_cfo_to_pat") is not None and not cq.get("lender"):
        add(f"3-year operating cash flow = {cq['three_year_cfo_to_pat']}x reported profit", "cash flow")
    if traj.get("quarters_with_yoy_revenue_growth"):
        add(f"Revenue grew YoY in {traj['quarters_with_yoy_revenue_growth']} recent quarters", "quarterly P&L")
    if ledger:
        add(f"Promises kept: {ledger['kept_of_measurable']} measurable targets", "promise ledger")
        for r in ledger["promises"]:
            if r["verdict"] in ("Kept", "Missed", "Partly", "Quietly dropped"):
                add(f"{r['verdict']}: {r['metric'].replace('_', ' ')} {r['horizon']} target {r['target']}"
                    + (f", actual {r['actual']:,.1f}" if r.get("actual") is not None else ""), "promise ledger")
    for d in dodged or []:
        if d.get("counts"):
            add(f"Call of {d['call']}: {d['summary']}", "dodged-question check")
    return facts


POSITIVE = re.compile(r"\b(strong|robust|healthy|improv\w*|record|best|accelerat\w*|momentum|expand\w*|better)\b", re.I)
METRIC_MAP = [("margin", re.compile(r"margin", re.I)), ("profit", re.compile(r"profit|pat\b|earnings", re.I)),
              ("revenue", re.compile(r"revenue|growth|sales|top ?line|demand", re.I))]


def narrative_vs_numbers(tables: dict, latest: Transcript | None) -> list[dict]:
    """Upbeat words in the latest call vs the latest quarter's numbers moving the other way."""
    if latest is None:
        return []
    q = tables["trajectory"].get("quarters") or []
    if len(q) < 5:
        return []
    cur, ya = q[-1], q[-5]
    moves = {}
    if cur.get("revenue") and ya.get("revenue"):
        moves["revenue"] = ("revenue", round((cur["revenue"] / ya["revenue"] - 1) * 100, 1), "% YoY")
    if cur.get("pat") and ya.get("pat") and ya["pat"] > 0:
        moves["profit"] = ("profit", round((cur["pat"] / ya["pat"] - 1) * 100, 1), "% YoY")
    if cur.get("ebitda_margin_pct") is not None and ya.get("ebitda_margin_pct") is not None:
        moves["margin"] = ("operating margin", round(cur["ebitda_margin_pct"] - ya["ebitda_margin_pct"], 1), " pts YoY")
    out, used = [], set()
    for t in latest.turns:
        if t.role != "management":
            continue
        for s in sentences(t.text):
            # Claims about now, not forecasts or hedged statements.
            if not POSITIVE.search(s) or re.search(r"\b(not|no|despite|although|while|will|would|expect\w*|going to|"
                                                    r"should|could|may|might|hope|if)\b", s, re.I):
                continue
            for key, rx in METRIC_MAP:
                if key in used or key not in moves or not rx.search(s):
                    continue
                name, change, unit = moves[key]
                if change < 0:
                    page = documents.find_quote(latest.pages, s)
                    if page:
                        out.append({"metric": name, "quote": s[:300], "page": page, "speaker": t.speaker, "call": latest.date,
                                    "url": latest.url, "numbers": f"{name} {change:+.1f}{unit} in quarter ended {cur['quarter_end']}"})
                        used.add(key)
                break
    return out[:3]


SYSTEM = (
    "You are writing for an equity investor. Using ONLY the numbered facts given, write exactly 3 bull points and 3 "
    "bear points about the company. Each point: one sentence, at most 160 characters, must include at least one "
    "number copied exactly from the facts it cites, and must list the fact ids it relies on. No adjectives without "
    "a number, no advice, no price targets, nothing that is not in the facts."
)
SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "array", "items": {"type": "object", "properties": {
        "text": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}},
        "required": ["text", "cites"]}} for k in ("bull", "bear")},
    "required": ["bull", "bear"],
}
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def check_bullet(b: dict, facts: dict[str, dict]) -> str | None:
    """None if the bullet stands on its cited facts, else the reason it is removed."""
    cites = [c for c in b.get("cites") or [] if c in facts]
    if not cites:
        return "cites no real fact"
    text = (b.get("text") or "").strip()
    if not text or len(text) > 200:
        return "empty or too long"
    pool = " ".join(facts[c]["text"] for c in cites).replace(",", "")
    nums = _NUM.findall(text)
    if not nums:
        return "no number"
    missing = [n for n in nums if n.replace(",", "") not in pool]
    if missing:
        return f"numbers not in cited facts: {missing}"
    if unsupported_adjectives(text):
        return "praise words without numbers"
    return None


def bull_bear(facts: list[dict], name: str) -> dict:
    if not facts:
        return {"bull": [], "bear": [], "removed": [], "note": "no facts"}
    prompt = f"Company: {name}\nFacts:\n" + "\n".join(f"{f['id']}: {f['text']} (source: {f['source']})" for f in facts)
    res = llm.router().complete("bull_bear", prompt, system=SYSTEM, tier="lite", schema=SCHEMA, max_tokens=1500)
    if not res or not isinstance(res.data, dict):
        return {"bull": [], "bear": [], "removed": [], "note": "model unavailable" if not llm.router().available else "no usable answer"}
    by_id = {f["id"]: f for f in facts}
    out = {"bull": [], "bear": [], "removed": []}
    for side in ("bull", "bear"):
        for b in (res.data.get(side) or [])[:3]:
            why = check_bullet(b, by_id)
            if why:
                out["removed"].append({"side": side, "text": b.get("text"), "why": why})
            else:
                out[side].append({"text": b["text"].strip(), "cites": [{"id": c, **by_id[c]} for c in b["cites"] if c in by_id]})
    return out
