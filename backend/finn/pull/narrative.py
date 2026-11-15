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


def revenue_jump(annual: list[dict], last_n: int = 3) -> tuple[str, float] | None:
    """A one-year revenue jump far above the company's usual growth within the last `last_n` years:
    usually a merger or acquisition, so multi-year growth is not like-for-like."""
    rows = [r for r in annual if r.get("revenue")]
    g = [(rows[i]["year_end"], (rows[i]["revenue"] / rows[i - 1]["revenue"] - 1) * 100)
         for i in range(1, len(rows)) if rows[i - 1]["revenue"] > 0]
    if len(g) < 4:
        return None
    for ye, x in g[-last_n:]:
        others = sorted(v for y, v in g if y != ye)
        med = others[len(others) // 2]
        if x >= 40 and x >= 2.5 * max(med, 5):
            return ye, round(x, 1)
    return None


def fact_pool(tables: dict, ledger: dict | None, dodged: list[dict] | None) -> list[dict]:
    """Numbered facts for the bull/bear writer. Python also computes comparison facts (growth slowing,
    margins squeezed, a merger-sized jump, per-share dilution) and marks each with the side it supports."""
    facts: list[dict] = []

    def add(text: str, source: str, tone: str | None = None):
        facts.append({"id": f"F{len(facts) + 1}", "text": text, "source": source, **({"tone": tone} if tone else {})})
    snap, traj, bs, cq = tables["snapshot"], tables["trajectory"], tables["balance_sheet"], tables["cash_quality"]
    lat = snap.get("latest") or {}
    if snap.get("pe"):
        add(f"P/E {snap['pe']:g}, market cap Rs {snap['market_cap_cr']:,.0f} cr", "screener ratios", "context")
    cagr = traj.get("cagr_pct") or {}
    c3 = cagr.get("3y") or {}
    diluted = c3.get("revenue") is not None and c3.get("eps") is not None and c3["revenue"] - c3["eps"] >= 10
    # A merger-sized year is called out only when per-share growth confirms it (shares were issued):
    # a fast-growing company with a big organic year is not accused of buying its growth.
    jump = revenue_jump(traj.get("annual") or []) if diluted else None
    if jump:
        add(f"3y revenue CAGR {c3['revenue']}% is not like-for-like: revenue jumped {jump[1]}% in the year to "
            f"{jump[0][:7]} while EPS grew only {c3['eps']}% a year (likely a merger or a large share issue)", "annual P&L", "bear")
    else:
        for n in ("3y", "5y"):
            c = cagr.get(n) or {}
            if c.get("revenue") is not None:
                add(f"{n} revenue CAGR {c['revenue']}%, profit CAGR {c.get('pat')}%", "annual P&L")
        if diluted:
            add(f"3y EPS CAGR {c3['eps']}% vs revenue CAGR {c3['revenue']}%: growth per share was much slower",
                "annual P&L", "bear")
    q = traj.get("quarters") or []
    g = g2 = None
    if len(q) >= 5 and q[-1].get("revenue") and q[-5].get("revenue"):
        g = round((q[-1]["revenue"] / q[-5]["revenue"] - 1) * 100, 1)
        add(f"Latest quarter ({q[-1]['quarter_end']}) revenue Rs {q[-1]['revenue']:,.0f} cr, {g:+.1f}% YoY", "quarterly P&L")
        if q[-1].get("pat") and q[-5].get("pat") and q[-5]["pat"] > 0:
            g2 = round((q[-1]["pat"] / q[-5]["pat"] - 1) * 100, 1)
            add(f"Latest quarter profit Rs {q[-1]['pat']:,.0f} cr, {g2:+.1f}% YoY", "quarterly P&L")
    if g is not None and c3.get("revenue") is not None and not jump:
        if g <= c3["revenue"] - 5:
            add(f"Revenue growth slowed: {g:+.1f}% YoY in the latest quarter vs a 3y CAGR of {c3['revenue']}%",
                "quarterly vs annual P&L", "bear")
        elif g >= c3["revenue"] + 5:
            add(f"Revenue growth sped up: {g:+.1f}% YoY in the latest quarter vs a 3y CAGR of {c3['revenue']}%",
                "quarterly vs annual P&L", "bull")
    if g is not None and g2 is not None and g > 0:
        if g2 <= g - 5:
            add(f"Profit grew slower than revenue ({g2:+.1f}% vs {g:+.1f}% YoY): margins were squeezed", "quarterly P&L", "bear")
        elif g2 >= g + 5:
            add(f"Profit grew faster than revenue ({g2:+.1f}% vs {g:+.1f}% YoY): margins widened", "quarterly P&L", "bull")
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
        for r in ledger["promises"]:
            if r["verdict"] in ("Kept", "Missed", "Partly", "Quietly dropped"):
                add(f"{r['verdict']}: {r['metric'].replace('_', ' ')} {r['horizon']} target {r['target']}"
                    + (f", actual {r['actual']:,.1f}" if r.get("actual") is not None else ""), "promise ledger",
                    "bull" if r["verdict"] == "Kept" else "bear")
    for d in dodged or []:
        # Only a real finding is a fact; "0 dodged" is not a bull point.
        if (d.get("counts") or {}).get("dodged"):
            add(f"Call of {d['call']}: {d['summary']}", "dodged-question check", "bear")
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
    "a number, no advice, no price targets, nothing that is not in the facts. A fact marked [bull] may only support "
    "a bull point and a fact marked [bear] only a bear point. A growth number is not a bear point by itself: use the "
    "comparison facts (slowing, squeezed, not like-for-like) for the bear case. Fewer points are fine if the facts are thin."
)
SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "array", "items": {"type": "object", "properties": {
        "text": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}},
        "required": ["text", "cites"]}} for k in ("bull", "bear")},
    "required": ["bull", "bear"],
}
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_FACT_REF = re.compile(r"\s*[\[(]\s*F\d+(?:\s*,\s*F\d+)*\s*[\])]")


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
    prompt = f"Company: {name}\nFacts:\n" + "\n".join(
        f"{f['id']}: {f['text']} (source: {f['source']})" + (f" [{f['tone']}]" if f.get("tone") else "") for f in facts)
    res = llm.router().complete("bull_bear", prompt, system=SYSTEM, tier="lite", schema=SCHEMA, max_tokens=1500)
    if not res or not isinstance(res.data, dict):
        return {"bull": [], "bear": [], "removed": [], "note": "model unavailable" if not llm.router().available else "no usable answer"}
    by_id = {f["id"]: f for f in facts}
    out = {"bull": [], "bear": [], "removed": []}
    for side in ("bull", "bear"):
        for b in (res.data.get(side) or [])[:3]:
            # The model sometimes writes its fact ids into the sentence ("... [F6]"); they are not part of the point.
            b = {**b, "text": _FACT_REF.sub("", b.get("text") or "").strip()}
            why = check_bullet(b, by_id) or next(
                (f"uses a [{by_id[c]['tone']}] fact" for c in b.get("cites") or []
                 if c in by_id and by_id[c].get("tone") and by_id[c]["tone"] != side), None)
            if why:
                out["removed"].append({"side": side, "text": b.get("text"), "why": why})
            else:
                out[side].append({"text": b["text"].strip(), "cites": [{"id": c, **by_id[c]} for c in b["cites"] if c in by_id]})
    return out


def finns_take(sections: dict) -> dict:
    """One line at the top of a company page, written by Python from facts already verified on the page:
    promises kept, growth trend, margins, a merger in the numbers, dodged questions, debt, cash."""
    S = sections or {}
    traj, bs, cq = S.get("trajectory") or {}, S.get("balance_sheet") or {}, S.get("cash_quality") or {}
    led, rc = S.get("promise_ledger") or {}, S.get("report_card") or {}
    parts: list[dict] = []          # {"text", "tone": good | bad | neutral}

    c = led.get("counts") or {}
    scored = (c.get("Kept") or 0) + (c.get("Partly") or 0) + (c.get("Missed") or 0)
    if scored:
        kept = c.get("Kept") or 0
        parts.append({"text": f"Kept {kept} of {scored} promise{'s' if scored != 1 else ''}",
                      "tone": "good" if kept / scored >= 0.6 else "bad" if kept / scored < 0.34 else "neutral"})
    elif led.get("promises"):
        n = len(led["promises"])
        parts.append({"text": f"{n} target{'s' if n != 1 else ''} tracked, none due yet", "tone": "neutral"})

    c3 = (traj.get("cagr_pct") or {}).get("3y") or {}
    q = traj.get("quarters") or []
    g = g2 = None
    if len(q) >= 5 and q[-1].get("revenue") and q[-5].get("revenue"):
        g = (q[-1]["revenue"] / q[-5]["revenue"] - 1) * 100
        if q[-1].get("pat") and q[-5].get("pat") and q[-5]["pat"] > 0:
            g2 = (q[-1]["pat"] / q[-5]["pat"] - 1) * 100
    jump = revenue_jump(traj.get("annual") or []) if (c3.get("revenue") is not None and c3.get("eps") is not None
                                                       and c3["revenue"] - c3["eps"] >= 10) else None
    if jump:
        parts.append({"text": f"3-year growth includes a one-off {jump[1]:.0f}% jump", "tone": "neutral"})
    elif g is not None and c3.get("revenue") is not None and c3["revenue"] < 0 < g:
        parts.append({"text": f"revenue rebounding (+{g:.0f}% YoY)", "tone": "good"})
    elif g is not None and c3.get("revenue") is not None:
        if g <= c3["revenue"] - 5:
            parts.append({"text": f"growth slowing {c3['revenue']:.0f}% \u2192 {g:.0f}%", "tone": "bad"})
        elif g >= c3["revenue"] + 5:
            parts.append({"text": f"growth speeding up {c3['revenue']:.0f}% \u2192 {g:.0f}%", "tone": "good"})
        else:
            parts.append({"text": f"growth steady at ~{g:.0f}%", "tone": "neutral"})
    if g is not None and g2 is not None:
        if g2 <= g - 5:
            parts.append({"text": "margins under pressure", "tone": "bad"})
        elif g2 >= g + 5:
            parts.append({"text": "margins widening", "tone": "good"})

    dodged = rc.get("questions_dodged")
    if dodged and not str(dodged).startswith("0 "):
        parts.append({"text": f"dodged {dodged} analyst questions", "tone": "bad"})
    if not cq.get("lender"):
        de = bs.get("debt_to_equity")
        if de is not None and de >= 1.5:
            parts.append({"text": f"high debt (D/E {de:g})", "tone": "bad"})
        r = cq.get("three_year_cfo_to_pat")
        if r is not None and r < 0.7:
            parts.append({"text": "profits not fully turning into cash", "tone": "bad"})
        elif r is not None and r >= 1.1 and len(parts) < 4:
            parts.append({"text": "profits backed by cash", "tone": "good"})
    return {"parts": parts[:4], "text": " \u00b7 ".join(x["text"] for x in parts[:4]),
            "note": "Written by Python from the verified facts on this page; no model involved."}


def _fy_quarter(iso: str) -> str:
    """'2026-09-30' -> 'Q2 FY27'."""
    y, m = int(iso[:4]), int(iso[5:7])
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(m)
    fy = y + 1 if m >= 4 else y
    return f"Q{q} FY{str(fy)[2:]}" if q else iso


def chart_notes(sections: dict) -> dict:
    """One plain sentence above each chart, computed by Python from the chart's own numbers."""
    S = sections or {}
    out: dict = {}
    q = (S.get("trajectory") or {}).get("quarters") or []
    lender = (S.get("snapshot") or {}).get("lender")
    if len(q) >= 5 and q[-1].get("revenue") and q[-5].get("revenue"):
        g = (q[-1]["revenue"] / q[-5]["revenue"] - 1) * 100
        s = f"{'Total income' if lender else 'Revenue'} {g:+.0f}% YoY in {_fy_quarter(q[-1]['quarter_end'])}"
        if q[-1].get("pat") is not None and q[-5].get("pat"):
            s += f"; profit {(q[-1]['pat'] / q[-5]['pat'] - 1) * 100:+.0f}%" if q[-5]["pat"] > 0 else "; profit up from a loss"
        m0, m1 = q[-5].get("ebitda_margin_pct"), q[-1].get("ebitda_margin_pct")
        if m0 is not None and m1 is not None:
            s += f"; operating margin {m1:.1f}% ({m1 - m0:+.1f} pts)"
        out["trajectory"] = s + "."
    ys = (S.get("cash_quality") or {}).get("years") or []
    ys = [y for y in ys if y.get("cfo") is not None and y.get("pat")]
    if ys and not (S.get("cash_quality") or {}).get("lender"):
        beat = sum(1 for y in ys if y["cfo"] >= y["pat"])
        out["cash"] = f"Cash from operations matched or beat profit in {beat} of the last {len(ys)} years."
    return out
