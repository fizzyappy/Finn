"""The Promise Ledger: what management said it would deliver, and what happened.

1. CANDIDATES  rules pick management sentences with a forward-looking cue and a
               number or metric word (most of a transcript never reaches the model).
2. EXTRACT     Gemini Flash-Lite turns candidates into strict JSON: metric, target,
               unit, horizon, firm/soft, and a verbatim quote.
3. VERIFY      every quote must be found word for word on its page (spacing
               ignored); if the model's quote is not verbatim, the source sentence
               itself is used (it is verbatim by construction); else dropped.
4. TRAIL       the same metric and horizon across calls: set, raised, cut, held,
               pushed out, quietly dropped.
5. MEASURE     Python computes the actual from the statement tables, in the same
               unit and period as the promise.
6. VERDICT     Python decides wherever a number exists: Kept, Partly, Missed,
               Too early, Quietly dropped, Not measurable. The reason line is
               written by Python from the numbers.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date

from .. import documents, fundamentals, llm
from . import periods
from .transcripts import Transcript

METRICS = ["revenue_growth", "revenue", "ebitda_margin", "ebit_margin", "pat_growth", "pat", "pat_margin",
           "roe", "net_debt", "deposit_growth", "loan_growth", "nim", "credit_cost", "working_capital", "capex",
           "order_inflow", "order_book", "volume_growth", "other"]
UNITS = ["pct_growth", "pct_margin", "rs_crore", "usd_million", "count", "none"]
LOWER_BETTER = {"net_debt"}

CUE = re.compile(
    r"\b(expect|guid|target|aim|aspir|anticipat|outlook|going forward|we will|we'll|we would|should (?:be|grow|see|come|remain)|"
    r"confident|on track|plan to|planning|intend|by fy|by the end of|next year|this year|for the year|in fy|for fy|"
    r"h2|second half|sustain|maintain|endeavou?r|visibility|commit|trajectory|band|range of|would be in|looking at)", re.I)
QUANT = re.compile(r"\d|single[- ]digit|double[- ]digit|teens|twenties|debt[- ]free|zero debt", re.I)
METRIC_WORDS = re.compile(r"revenue|growth|margin|ebitda|ebit|profit|pat|debt|capex|order|volume|deposit|loan|"
                          r"advances|nim|credit cost|roe|roa|stores|capacity|top ?line|bottom ?line", re.I)

SYSTEM = (
    "You extract forward-looking commitments that company MANAGEMENT made on an earnings call, for an investor "
    "tracking whether management keeps its word. Use only the numbered sentences given. Skip statements about "
    "the past, analysts' words, and vague hopes with no measurable target unless they name a clear deliverable. "
    "metric: use ebit_margin when they say 'operating margin' or 'EBIT margin', ebitda_margin for EBITDA margin. "
    "unit: pct_growth for growth rates, pct_margin for margins, rs_crore for rupee amounts (convert lakh crore x "
    "100000 is NOT allowed: give the number as said and say the unit in basis), none if there is no number. "
    "horizon: the period exactly as said ('FY27', 'H2', 'this year', 'next 2-3 years'). scope: 'company' if the "
    "target is for the whole company or group, otherwise the segment or business exactly as named (e.g. 'core "
    "E&C', 'domestic decorative'). firmness: firm for 'will/guide/target', soft for 'hope/aspire/should'. quote: "
    "copy the shortest exact span from the sentence that contains the commitment, word for word."
)
SCHEMA = {
    "type": "object",
    "properties": {"promises": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "i": {"type": "integer"},
            "metric": {"type": "string", "enum": METRICS},
            "target_low": {"type": "number"},
            "target_high": {"type": "number"},
            "unit": {"type": "string", "enum": UNITS},
            "basis": {"type": "string", "description": "e.g. constant currency, reported INR, YoY, lakh crore"},
            "horizon": {"type": "string"},
            "scope": {"type": "string"},
            "firmness": {"type": "string", "enum": ["firm", "soft"]},
            "quote": {"type": "string"},
        },
        "required": ["i", "metric", "unit", "horizon", "scope", "firmness", "quote"]}}},
    "required": ["promises"],
}


@dataclass
class Promise:
    metric: str
    unit: str
    low: float | None
    high: float | None
    basis: str
    horizon_text: str
    horizon: str              # resolved label: FY27, H2FY27, Q3FY27, by FY30, open
    horizon_end: str | None   # ISO date when it can be measured
    firmness: str
    quote: str
    page: int
    speaker: str
    call_date: str
    source_url: str
    quote_method: str = "model"     # model | source sentence
    scope: str = "company"
    sentence: str = ""              # the full source sentence (for basis words the quote may leave out)

    @property
    def company_wide(self) -> bool:
        return bool(re.fullmatch(r"\s*(company|group|consolidated|overall|whole company|total|firm[- ]?wide|"
                                 r"company[- ]wide|bank|the bank|standalone)\s*", self.scope or "company", re.I))

    def target_text(self) -> str:
        u = {"pct_growth": "%", "pct_margin": "%", "rs_crore": " cr", "usd_million": " USD mn"}.get(self.unit, "")
        if self.low is not None and self.high is not None and self.low != self.high:
            return f"{self.low:g}-{self.high:g}{u}"
        v = self.low if self.low is not None else self.high
        return f"{v:g}{u}" if v is not None else "no number"


# ------------------------------------------------------------------ 1-3: candidates, extract, verify
def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text) if len(s.strip()) > 25]


def candidates(tr: Transcript, limit: int = 90) -> list[dict]:
    out = []
    for t in tr.turns:
        if t.role != "management":
            continue
        for s in sentences(t.text):
            if CUE.search(s) and QUANT.search(s) and METRIC_WORDS.search(s):
                out.append({"sentence": s[:500], "page": t.page, "speaker": t.speaker})
    return out[:limit]


def extract(tr: Transcript) -> tuple[list[Promise], dict]:
    cands = candidates(tr)
    stats = {"candidates": len(cands), "extracted": 0, "verified": 0, "quote_replaced": 0, "dropped": 0}
    if not cands:
        return [], stats
    call = date.fromisoformat(tr.date) if tr.date else date.today()
    prompt = f"Call date: {tr.date}\n" + "\n".join(f"{i}. [{c['speaker']}] {c['sentence']}" for i, c in enumerate(cands))
    res = llm.router().complete("promise_extract", prompt, system=SYSTEM, tier="lite", schema=SCHEMA, max_tokens=6000)
    if not res or not isinstance(res.data, dict):
        stats["error"] = "model unavailable" if not llm.router().available else "no usable answer"
        return [], stats
    out = []
    for p in res.data.get("promises") or []:
        stats["extracted"] += 1
        i = p.get("i")
        if not isinstance(i, int) or not 0 <= i < len(cands):
            stats["dropped"] += 1
            continue
        c = cands[i]
        quote, method = (p.get("quote") or "").strip(), "model"
        if not quote or documents.quote_key(quote) not in documents.quote_key(c["sentence"]):
            quote, method = c["sentence"], "source sentence"
            stats["quote_replaced"] += 1
        page = documents.find_quote(tr.pages, quote)
        if page is None:
            stats["dropped"] += 1
            continue
        stats["verified"] += 1
        h = periods.resolve(p.get("horizon") or "", call)
        out.append(Promise(
            metric=p["metric"], unit=p["unit"], low=p.get("target_low"), high=p.get("target_high"),
            basis=p.get("basis") or "", horizon_text=p.get("horizon") or "",
            horizon=h.label if h.kind != "multi" else f"by {periods.label(h.fy)}",
            horizon_end=h.end.isoformat() if h.end else None, firmness=p.get("firmness") or "soft",
            quote=quote, page=page, speaker=c["speaker"], call_date=tr.date, source_url=tr.url, quote_method=method,
            scope=p.get("scope") or "company", sentence=c["sentence"]))
    return out, stats


# ------------------------------------------------------------------ 5: measure
def _annual_row(f: dict, fy: int) -> dict | None:
    return f["annual"].get(f"{fy}-03-31")


def _sum_quarters(f: dict, ends: list[date], key: str) -> float | None:
    vals = [(f["quarterly"].get(e.isoformat()) or {}).get(key) for e in ends]
    return None if any(v is None for v in vals) else sum(vals)


def _period_values(f: dict, kind: str, fy: int, part: int | None) -> tuple[dict | None, dict | None, str]:
    """(this period, same period a year earlier, label) with revenue/ebitda/pat/depreciation."""
    keys = ("revenue", "ebitda", "pat", "depreciation", "other_income")
    if kind in ("FY", "multi"):
        cur, prev = _annual_row(f, fy), _annual_row(f, fy - 1)
        return cur, prev, periods.label(fy)
    ends = periods.quarters_of(fy, part) if kind == "H" else [periods.quarter_end(fy, part)]
    prev_ends = [e.replace(year=e.year - 1) for e in ends]
    cur = {k: _sum_quarters(f, ends, k) for k in keys}
    prev = {k: _sum_quarters(f, prev_ends, k) for k in keys}
    if cur.get("revenue") is None:
        return None, None, ""
    return cur, prev, periods.label(fy, q=part if kind == "Q" else None, half=part if kind == "H" else None)


def measure(p: Promise, f: dict, today: date | None = None) -> dict:
    """Actual in the promise's own unit, from the statement tables. Never from a model."""
    today = today or date.today()
    if p.horizon_end is None:
        return {"status": "not_measurable", "why": "no date was given for this target"}
    if not p.company_wide:
        return {"status": "not_measurable", "why": f"target is for '{p.scope}', not the whole company; the tables are company-wide"}
    if p.unit in ("usd_million", "count", "none") or p.metric in (
            "capex", "order_inflow", "order_book", "volume_growth", "other", "loan_growth", "nim", "credit_cost", "working_capital"):
        return {"status": "not_measurable", "why": f"{p.metric.replace('_', ' ')} is not in the reported statement tables"}
    if p.metric in ("revenue_growth", "pat_growth") and re.search(
            r"constant currency|\bcc\b|usd|dollar", f"{p.basis} {p.quote} {p.sentence}", re.I):
        return {"status": "not_measurable", "why": "guided in constant currency / USD; the statements report INR"}
    if p.unit == "rs_crore" and re.search(r"lakh crore|billion|million|mn\b|bn\b", p.basis, re.I):
        return {"status": "not_measurable", "why": f"target unit '{p.basis}' differs from the tables (Rs crore)"}
    h = periods.resolve(p.horizon_text, date.fromisoformat(p.call_date))
    latest_q = max((k for k in f["quarterly"] if k[:4].isdigit()), default="")
    if p.metric == "deposit_growth":
        cur, prev = (f["balance_sheet"].get(f"{h.fy}-03-31") or {}), (f["balance_sheet"].get(f"{h.fy - 1}-03-31") or {})
        if h.fy is None or not cur.get("deposits"):
            return {"status": "too_early" if h.end and h.end.isoformat() > latest_q else "not_measurable", "why": "no deposits figure yet"}
        g = fundamentals.growth_pct(cur["deposits"], prev.get("deposits"))[0]
        return {"status": "measured", "actual": g, "period": periods.label(h.fy), "how": "deposit growth, balance sheet"}
    cur, prev, lab = _period_values(f, h.kind, h.fy, h.part) if h.fy else (None, None, "")
    if not cur:
        if h.end and h.end.isoformat() > latest_q:
            return {"status": "too_early", "why": f"{p.horizon} has not been reported yet (latest quarter {latest_q})"}
        return {"status": "not_measurable", "why": "the period is not in the tables"}
    rev, eb, pat = cur.get("revenue"), cur.get("ebitda"), cur.get("pat")
    m = p.metric
    if m == "revenue_growth":
        v, how = fundamentals.growth_pct(rev, (prev or {}).get("revenue"))[0], "revenue growth YoY (reported INR)"
    elif m == "pat_growth":
        v, how = fundamentals.growth_pct(pat, (prev or {}).get("pat"))[0], "net profit growth YoY"
    elif m == "revenue":
        v, how = rev, "revenue, Rs crore"
    elif m == "pat":
        v, how = pat, "net profit, Rs crore"
    elif m == "ebitda_margin":
        v, how = (round(eb / rev * 100, 1) if rev and eb is not None else None), "EBITDA (operating profit) / revenue"
    elif m == "ebit_margin":
        dep = cur.get("depreciation")
        v = round((eb - dep) / rev * 100, 1) if rev and eb is not None and dep is not None else None
        how = "EBIT (operating profit - depreciation) / revenue"
    elif m == "pat_margin":
        v, how = (round(pat / rev * 100, 1) if rev and pat is not None else None), "net profit / revenue"
    elif m == "net_debt":
        bs = f["balance_sheet"].get(f"{h.fy}-03-31") or {}
        v, how = bs.get("borrowings"), "gross borrowings at year end (cash not netted: approximate)"
    elif m == "roe" and h.kind in ("FY", "multi"):
        b1, b0 = f["balance_sheet"].get(f"{h.fy}-03-31") or {}, f["balance_sheet"].get(f"{h.fy - 1}-03-31") or {}
        nw = [(b.get("equity_capital") or 0) + (b.get("reserves") or 0) for b in (b0, b1) if b.get("reserves") is not None]
        v = round(pat / (sum(nw) / len(nw)) * 100, 1) if pat and len(nw) == 2 else None
        how = "net profit / average net worth (equity + reserves)"
    else:
        v, how = None, ""
    if v is None:
        return {"status": "not_measurable", "why": "could not compute this from the tables"}
    return {"status": "measured", "actual": v, "period": lab, "how": how}


# ------------------------------------------------------------------ 6: verdict
def verdict(p: Promise, actual: float) -> tuple[str, str]:
    lo, hi = p.low, p.high
    if lo is None and hi is None:
        return "not_measurable", "no number in the promise"
    pct = p.unit in ("pct_growth", "pct_margin")
    floor = lo if lo is not None else hi
    ceiling = hi if hi is not None else lo
    tol = 0.5 if pct else abs(floor) * 0.03
    band = 2.0 if pct else abs(floor) * 0.10
    unit = "%" if pct else " cr"
    if p.metric in LOWER_BETTER:
        if actual <= ceiling + tol:
            return "kept", f"target at most {ceiling:g}{unit}, actual {actual:,.1f}{unit}"
        return ("partly" if actual <= ceiling + band else "missed"), f"target at most {ceiling:g}{unit}, actual {actual:,.1f}{unit}"
    tgt = p.target_text()
    # Far above the target usually means the target was for something else (a segment,
    # another basis). Do not score it; say so.
    if (pct and actual > ceiling + max(5.0, abs(ceiling))) or (not pct and actual > 2 * abs(ceiling)):
        return "not_measurable", (f"actual {actual:,.1f}{unit} is far above the target {tgt}; the target probably refers to "
                                  "a different scope or basis, so it is not scored")
    if actual >= floor - tol:
        return "kept", f"target {tgt}, actual {actual:,.1f}{unit}"
    if actual >= floor - band:
        return "partly", f"target {tgt}, actual {actual:,.1f}{unit} (just short)"
    return "missed", f"target {tgt}, actual {actual:,.1f}{unit}"


# ------------------------------------------------------------------ 4: trail
def _mid(p: Promise) -> float | None:
    vals = [v for v in (p.low, p.high) if v is not None]
    return sum(vals) / len(vals) if vals else None


# Managements label the same target loosely ("margin" = EBIT or EBITDA): a later mention
# of any metric in the family means the topic was not dropped.
FAMILY = {"ebit_margin": "margin", "ebitda_margin": "margin", "pat_margin": "margin",
          "revenue_growth": "revenue", "revenue": "revenue", "pat_growth": "profit", "pat": "profit"}


def trails(promises: list[Promise], call_dates: list[str]) -> list[dict]:
    """Group statements on the same metric and horizon across calls, oldest first."""
    groups: dict[tuple, list[Promise]] = {}
    for p in sorted(promises, key=lambda x: x.call_date):
        # A company-wide target and a segment target are different promises.
        scope = "company" if p.company_wide else re.sub(r"\W+", " ", p.scope.lower()).strip()
        groups.setdefault((p.metric, p.horizon, p.unit, scope), []).append(p)
    out = []
    for (metric, horizon, unit, _scope), ps in groups.items():
        events, prev = [], None
        by_call: dict[str, Promise] = {}
        for p in ps:
            by_call[p.call_date] = p          # one statement per call: the last one
        for d in sorted(by_call):
            p = by_call[d]
            m = _mid(p)
            if prev is None:
                ev = "set"
            elif m is None or _mid(prev) is None:
                ev = "repeated"
            else:
                tol = 0.25 if unit in ("pct_growth", "pct_margin") else abs(_mid(prev)) * 0.02
                ev = "raised" if m > _mid(prev) + tol else "cut" if m < _mid(prev) - tol else "held"
            events.append({"call": d, "event": ev, "target": p.target_text(), "quote": p.quote, "page": p.page,
                           "url": p.source_url})
            prev = p
        last = by_call[max(by_call)]
        later = [d for d in call_dates if d > last.call_date and (last.horizon_end is None or d <= last.horizon_end)]
        has_number = last.low is not None or last.high is not None
        if later and has_number:
            fam = FAMILY.get(metric, metric)
            same_metric = [q for q in promises if FAMILY.get(q.metric, q.metric) == fam and q.call_date in later]
            moved = [q for q in same_metric if q.horizon_end and last.horizon_end and q.horizon_end > last.horizon_end]
            if moved:
                ev = "pushed out"
            elif same_metric or metric == "other":
                ev = "not repeated yet"     # the metric is still discussed, for other periods
            else:
                # "Quietly dropped" is a strong charge: it needs two later calls with no word on this metric.
                ev = "quietly dropped" if len(later) >= 2 else "not repeated yet"
            events.append({"call": later[-1], "event": ev, "target": moved[-1].horizon if moved else None,
                           "quote": None, "page": None, "url": None, "silent_calls": len(later)})
        # Judge on the latest statement that carries a number ("double-digit growth" later
        # does not erase an earlier "10% to 11%").
        numeric = [by_call[d] for d in sorted(by_call) if by_call[d].low is not None or by_call[d].high is not None]
        out.append({"metric": metric, "horizon": horizon, "unit": unit, "events": events,
                    "latest": numeric[-1] if numeric else last})
    return out


EXPLAIN = re.compile(r"\b(because|due to|on account of|impacted|impact of|owing to|driven by|reason|headwind|"
                     r"pressure|delay|slower|softer|weak)\b", re.I)
METRIC_TERMS = {"revenue_growth": "revenue|top ?line|sales", "revenue": "revenue|top ?line|sales", "ebitda_margin": "margin|ebitda",
                "ebit_margin": "margin|ebit|operating", "pat_growth": "profit|pat|bottom", "pat": "profit|pat",
                "pat_margin": "margin|profit", "net_debt": "debt|borrowing", "deposit_growth": "deposit"}


def explanation(metric: str, after: str, transcripts: list[Transcript], horizon: str = "") -> dict | None:
    """Management's own explanation from a later call: a management sentence on the
    same metric with a cause word (bonus if it names the period). Verified on its page."""
    terms = re.compile(METRIC_TERMS.get(metric, metric.replace("_", " ")), re.I)
    hz = re.compile(re.escape(horizon).replace("FY", r"FY\s*'?"), re.I) if horizon else None
    best = None
    for tr in transcripts:
        if tr.date <= after:
            continue
        for t in tr.turns:
            if t.role != "management":
                continue
            for s in sentences(t.text):
                about_period = (hz and hz.search(s)) or re.search(r"last year|full year|for the year|previous year", s, re.I)
                if terms.search(s) and EXPLAIN.search(s) and about_period and 40 < len(s) < 400:
                    score = len(terms.findall(s)) + len(EXPLAIN.findall(s))
                    if not best or score > best[0]:
                        best = (score, s, tr, t)
    if not best:
        return None
    _, s, tr, t = best
    page = documents.find_quote(tr.pages, s)
    return {"quote": s, "page": page, "speaker": t.speaker, "call": tr.date, "url": tr.url} if page else None


# ------------------------------------------------------------------ ledger
LABEL = {"kept": "Kept", "partly": "Partly", "missed": "Missed", "too_early": "Too early",
         "quietly_dropped": "Quietly dropped", "not_measurable": "Not measurable"}


def harmonise_scopes(ps: list[Promise]) -> int:
    """The model sometimes labels the same target 'company' in one call and by its
    segment in another. A 'company' statement with the same metric family, period and
    target as a segment statement takes the segment's scope. Returns how many changed."""
    changed = 0
    segs = [q for q in ps if not q.company_wide]
    for p in ps:
        if not p.company_wide or _mid(p) is None:
            continue
        for q in segs:
            if FAMILY.get(q.metric, q.metric) == FAMILY.get(p.metric, p.metric) and q.horizon == p.horizon \
                    and _mid(q) is not None and abs(_mid(q) - _mid(p)) < 0.3:
                p.scope = q.scope
                changed += 1
                break
    return changed


def ledger(transcripts: list[Transcript], f: dict, today: date | None = None) -> dict:
    all_p, stats = [], []
    for tr in transcripts:
        ps, st = extract(tr)
        all_p += ps
        stats.append({"call": tr.date, **st})
    stats.append({"scopes_harmonised": harmonise_scopes(all_p)})
    call_dates = sorted(tr.date for tr in transcripts)
    rows = []
    for tg in trails(all_p, call_dates):
        p: Promise = tg["latest"]
        meas = measure(p, f, today)
        dropped = tg["events"][-1]["event"] == "quietly dropped"
        if meas["status"] == "measured":
            v, why = verdict(p, meas["actual"])
            why = f"{why} ({meas['period']}, {meas['how']})"
            if v == "not_measurable" and dropped:
                v = "quietly_dropped"
        elif dropped:
            v, why = "quietly_dropped", f"not mentioned again after the {p.call_date} call"
        else:
            v, why = meas["status"], meas.get("why", "")
        row = {"metric": p.metric, "scope": p.scope, "horizon": p.horizon, "target": p.target_text(), "firmness": p.firmness,
               "verdict": LABEL[v], "reason": why, "actual": meas.get("actual"), "said": asdict(p),
               "trail": tg["events"]}
        if v in ("missed", "partly") or any(e["event"] == "cut" for e in tg["events"]):
            row["management_explanation"] = explanation(p.metric, p.call_date, transcripts, p.horizon)
        rows.append(row)
    order = {"Missed": 0, "Partly": 1, "Quietly dropped": 2, "Kept": 3, "Too early": 4, "Not measurable": 5}
    rows.sort(key=lambda r: (order[r["verdict"]], r["said"]["call_date"]), reverse=False)
    counts = {k: sum(1 for r in rows if r["verdict"] == k) for k in order}
    scored = counts["Kept"] + counts["Partly"] + counts["Missed"]
    return {"promises": rows, "counts": counts, "kept_of_measurable": f"{counts['Kept']} of {scored}" if scored else "none measurable yet",
            "extraction": stats, "calls": call_dates}


def vs_guidance(ledger_result: dict, quarter_end: str) -> list[dict]:
    """Hook for the push Results card: open targets that cover the quarter just reported."""
    out = []
    for r in ledger_result.get("promises", []):
        end = r["said"].get("horizon_end")
        if end and end >= quarter_end and r["verdict"] in ("Too early", "Kept", "Partly", "Missed") \
                and r["said"]["unit"] in ("pct_growth", "pct_margin"):
            out.append({"metric": r["metric"], "horizon": r["horizon"], "target": r["target"],
                        "quote": r["said"]["quote"], "said_on": r["said"]["call_date"]})
    return out
