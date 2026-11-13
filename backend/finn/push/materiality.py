"""Materiality: how much should this filing interrupt the investor?

score = base(category/subtype)            what kind of event it is
        x event modifiers                  senior role, abrupt vs planned exit, size vs market cap,
                                           internal restructuring, allotment of an already-announced issue
        x holding weight                   bigger positions matter more
        x your preference for the category
        + market-reaction bonus            the stock moved unusually around the filing
clipped to 0..1.

Treatment: hero >= 0.6, one-liner 0.3-0.6, collapsed below 0.3 (routine
paperwork is always collapsed). Every factor is returned in `score_parts`, so
the app can answer "why am I seeing this?". All arithmetic is here, in Python.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .taxonomy import Classification

HERO, ONE_LINER = 0.6, 0.3

AMOUNT = re.compile(
    r"(?:rs\.?|inr|₹|usd|us\$|\$)\s*([\d,]+(?:\.\d+)?)\s*(crores?|cr\b\.?|lakhs?|lacs?|million|mn\b|billion|bn\b)", re.I)
UNIT_TO_CR = {"crore": 1, "crores": 1, "cr": 1, "cr.": 1, "lakh": 0.01, "lakhs": 0.01, "lac": 0.01, "lacs": 0.01,
              "million": 0.1, "mn": 0.1, "billion": 100, "bn": 100}
USD_TO_INR = 85.0   # rough, only to size a USD amount against market cap; flagged in the reason


def extract_amount_cr(text: str) -> tuple[float, str] | None:
    """Largest money amount in the text, in Rs crore, with the matched words."""
    best = None
    for m in AMOUNT.finditer(text or ""):
        unit = m.group(2).lower().rstrip(".")
        v = float(m.group(1).replace(",", "")) * UNIT_TO_CR.get(unit, 1)
        if re.match(r"usd|us\$|\$", m.group(0), re.I):
            v *= USD_TO_INR          # e.g. US$ 500 million = 50 "crore dollars" = Rs 4,250 crore
        if best is None or v > best[0]:
            best = (v, m.group(0).strip())
    return best


@dataclass
class Score:
    value: float
    treatment: str
    parts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": self.value, "treatment": self.treatment, "score_parts": self.parts}


def weight_factor(weight: float | None) -> float:
    """0.9x for a tiny position, 1.0x at 5%, up to 1.2x at 15%+."""
    if not weight:
        return 1.0
    return round(min(1.2, max(0.9, 0.9 + 2 * weight)), 3)


def treatment_for(score: float, routine: bool) -> str:
    if routine:
        return "collapsed"
    return "hero" if score >= HERO else "one_liner" if score >= ONE_LINER else "collapsed"


def score(f: dict, c: Classification, *, weight: float | None = None, mcap_cr: float | None = None,
          prefs: dict | None = None, reaction: dict | None = None) -> Score:
    text = " ".join(str(f.get(k) or "") for k in ("subject", "category", "detail"))
    parts = [{"factor": "base", "value": c.base, "why": f"{c.category.replace('_', ' ')} / {c.subtype.replace('_', ' ')}"}]
    s = c.base

    def mult(x: float, why: str):
        nonlocal s
        s *= x
        parts.append({"factor": "multiply", "value": round(x, 3), "why": why})

    if c.category == "management_change":
        if re.search(r"re-?appoint|superannuat|retire|completion of (his|her|the) (term|tenure)|end of (his|her) term", text, re.I):
            mult(0.6, "planned change (reappointment / retirement)")
        elif re.search(r"with immediate effect|personal reasons|sudden|unexpected|demise", text, re.I):
            mult(1.25, "abrupt exit")
    if c.category == "M&A" and re.search(r"wholly[- ]owned|step[- ]down subsidiar|internal restructuring", text, re.I):
        mult(0.6, "internal restructuring (wholly owned subsidiary)")
    if c.category == "fund_raise" and re.search(r"\ballot(ment|ted)\b", text, re.I):
        mult(0.8, "allotment of an issue already announced")
    if c.category in ("M&A", "fund_raise", "press_release", "capex", "litigation"):
        amt = extract_amount_cr(text)
        if amt and mcap_cr:
            ratio = amt[0] / mcap_cr
            x = 1.5 if ratio >= 0.05 else 1.25 if ratio >= 0.01 else 0.7 if ratio < 0.002 else 1.0
            if x != 1.0:
                mult(x, f"size: {amt[1]} is {ratio:.1%} of market cap (Rs {mcap_cr:,.0f} cr)")
    pref = (prefs or {}).get(c.category, 1.0)
    if pref != 1.0:
        mult(pref, f"your preference for {c.category.replace('_', ' ')}")
    wf = weight_factor(weight)
    if wf != 1.0:
        mult(wf, f"holding weight {weight:.1%}")
    if reaction and (abs(reaction.get("z") or 0) >= 2 or (reaction.get("vol_x") or 0) >= 2):
        s += 0.1
        parts.append({"factor": "add", "value": 0.1,
                      "why": f"stock moved unusually on {reaction.get('date')}: {reaction.get('ret_pct', 0):+.1f}% "
                             f"({reaction.get('z', 0):+.1f} sigma vs its normal), volume {reaction.get('vol_x', 0):.1f}x"})
    s = round(max(0.0, min(1.0, s)), 3)
    if c.routine:
        parts.append({"factor": "rule", "value": 0, "why": "routine paperwork: always collapsed"})
    return Score(s, treatment_for(s, c.routine), parts)
