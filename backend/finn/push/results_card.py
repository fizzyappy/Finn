"""Results card: the quarter's numbers read from the results filing itself, then verified.

1. Find the pages that hold the results table (SEBI format: revenue, profit before
   tax, "quarter ended" columns). Prefer the consolidated statement.
2. Send only those pages, as a small PDF, to Gemini Flash-Lite. It *reads* the
   numbers for the current, previous and year-ago quarter. It does no maths.
3. Python checks the answer: three quarters 3 and 12 months apart, PBT - tax = PAT,
   total income = revenue + other income, a known unit, and agreement with
   screener's quarterly table. Pass -> "verified". Fail -> retry with Gemini Flash.
   Still failing -> the card says "not verified" and links the filing.
4. Python computes EBITDA (when not stated), margins, QoQ and YoY.
Banks: net interest income, operating profit, provisions, PAT, gross/net NPA.
"""
from __future__ import annotations

import io
import re
from datetime import date

from .. import documents, fundamentals, llm

UNIT_TO_CR = {"crore": 1.0, "lakh": 0.01, "million": 0.1, "thousand": 0.0001, "rupees": 1e-7}
LINES = ("revenue_from_operations", "excise_duty", "other_income", "total_income", "finance_costs", "depreciation",
         "profit_before_exceptional_and_tax", "exceptional_items", "profit_before_tax", "tax_expense",
         "profit_after_tax", "profit_attributable_to_owners",
         "interest_earned", "interest_expended", "operating_profit_before_provisions", "provisions",
         "gross_npa_pct", "net_npa_pct")

SYSTEM = (
    "You read Indian listed-company quarterly financial results statements (SEBI format). Copy numbers exactly as "
    "printed; brackets mean negative. Do not calculate anything. Use the first three period columns: current "
    "period, preceding period, and the same period of the previous year (ignore year-to-date and full-year columns). "
    "Companies that report half-yearly have half-year columns: use those. Each line is a list of three numbers in "
    "that order. Report excise duty separately if it is printed as its own line. Leave out lines that are not printed."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "basis": {"type": "string", "enum": ["consolidated", "standalone"]},
        "unit": {"type": "string", "enum": list(UNIT_TO_CR)},
        "is_bank_or_nbfc_format": {"type": "boolean"},
        "period_ends": {"type": "array", "items": {"type": "string"},
                        "description": "YYYY-MM-DD for current, preceding, year-ago quarter"},
        "lines": {"type": "object", "properties": {k: {"type": "array", "items": {"type": "number"}} for k in LINES}},
    },
    "required": ["basis", "unit", "is_bank_or_nbfc_format", "period_ends", "lines"],
}

SCANNED_MAX_PAGES = 25

_REV = re.compile(r"revenue from operations|income from operations|interest earned|total revenue", re.I)
_PBT = re.compile(r"profit\s*/?\s*\(?(loss)?\)?\s*before\s*(exceptional|tax)", re.I)
_QTR = re.compile(r"quarter|three months|half[- ]year", re.I)
_TITLE = re.compile(r"statement of .{0,60}results|financial results for the", re.I)
_CONS = re.compile(r"consolidated", re.I)
_STAND = re.compile(r"standalone", re.I)


def find_result_pages(pages: list[str]) -> tuple[list[int], str]:
    """0-based indexes of the results-table pages, and the basis they show."""
    hits = []
    for i, p in enumerate(pages):
        score = bool(_REV.search(p)) + bool(_PBT.search(p)) + bool(_QTR.search(p)) + bool(_TITLE.search(p))
        nums = len(re.findall(r"\d[\d,]*\.\d+|\(\d[\d,]*\)", p))
        if score >= 3 and _REV.search(p) and nums >= 25:
            basis = "consolidated" if _CONS.search(p[:1500]) and not _STAND.search(p[:600]) else \
                    "standalone" if _STAND.search(p[:1500]) else "unknown"
            hits.append((i, basis))
    cons = [i for i, b in hits if b == "consolidated"]
    if cons:
        return cons[:2], "consolidated"
    return [i for i, _ in hits][:2], (hits[0][1] if hits else "unknown")


def mini_pdf(pdf_path: str, page_idx: list[int]) -> bytes:
    from pypdf import PdfReader, PdfWriter

    r = PdfReader(pdf_path)
    w = PdfWriter()
    for i in page_idx:
        w.add_page(r.pages[i])
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _months_between(a: str, b: str) -> int | None:
    try:
        da, db = date.fromisoformat(a), date.fromisoformat(b)
    except (TypeError, ValueError):
        return None
    return (da.year - db.year) * 12 + da.month - db.month


def _close(a: float, b: float, rel: float, abs_tol: float) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b)))


def period_type(ex: dict) -> str | None:
    """'quarter' (columns 3 and 12 months apart) or 'half_year' (6 and 12: SME platform reporters)."""
    pe = ex.get("period_ends") or []
    if len(pe) != 3:
        return None
    gaps = (_months_between(pe[0], pe[1]), _months_between(pe[0], pe[2]))
    return {(3, 12): "quarter", (6, 12): "half_year"}.get(gaps)


def reorder(ex: dict) -> dict:
    """Some statements print columns in an unusual order. If the three period dates
    are valid, put them in (current, preceding, year-ago) order by date, moving each
    line's values with them. Pure bookkeeping, done in Python."""
    pe = ex.get("period_ends") or []
    try:
        ds = [date.fromisoformat(p) for p in pe]
    except (TypeError, ValueError):
        return ex
    if len(ds) != 3 or len(set(ds)) != 3:
        return ex
    cur = max(ds)
    ya = [i for i, d in enumerate(ds) if (cur.year - d.year) * 12 + cur.month - d.month == 12]
    rest = [i for i in range(3) if i != ds.index(cur) and i not in ya[:1]]
    if not ya or len(rest) != 1:
        return ex
    order = [ds.index(cur), rest[0], ya[0]]
    if order == [0, 1, 2]:
        return ex
    lines = {k: ([v[i] for i in order] if len(v) == 3 else v) for k, v in (ex.get("lines") or {}).items()}
    return {**ex, "period_ends": [pe[i] for i in order], "lines": lines, "reordered_columns": True}


def net_revenue(L: dict) -> list[float] | None:
    rev, exc = L.get("revenue_from_operations"), L.get("excise_duty")
    if rev and exc and len(rev) == len(exc) == 3:
        return [r - e for r, e in zip(rev, exc)]
    return rev


def check(ex: dict, screener_q: dict | None, screener_basis: str | None) -> list[dict]:
    """Deterministic checks on an extracted statement. Returns [{name, ok, detail}]."""
    out = []
    L = ex.get("lines") or {}
    pe = ex.get("period_ends") or []
    three = len(pe) == 3 and all(len(v) == 3 for v in L.values())
    out.append({"name": "three periods", "ok": three, "detail": f"{len(pe)} period dates; lines with 3 values: "
                f"{sum(len(v) == 3 for v in L.values())}/{len(L)}"})
    if len(pe) == 3:
        q, y = _months_between(pe[0], pe[1]), _months_between(pe[0], pe[2])
        pt = period_type(ex)
        out.append({"name": "periods line up (3/12 or 6/12 months apart)", "ok": pt is not None,
                    "detail": f"{q} and {y} months apart" + (f": {pt.replace('_', '-')} reporting" if pt else "")})
    out.append({"name": "unit known", "ok": ex.get("unit") in UNIT_TO_CR, "detail": ex.get("unit")})
    bank = ex.get("is_bank_or_nbfc_format")
    need = ("interest_earned", "profit_before_tax", "profit_after_tax") if bank else \
           ("revenue_from_operations", "profit_before_tax", "profit_after_tax")
    missing = [k for k in need if len(L.get(k) or []) != 3]
    out.append({"name": "key lines present", "ok": not missing, "detail": "missing: " + ", ".join(missing) if missing else "ok"})
    pbt, tax, pat = L.get("profit_before_tax"), L.get("tax_expense"), L.get("profit_after_tax")
    if pbt and tax and pat and len(pbt) == len(tax) == len(pat) == 3:
        bad = [i for i in range(3) if not _close(pbt[i] - tax[i], pat[i], 0.02, 0.6)]
        out.append({"name": "PBT - tax = PAT", "ok": not bad,
                    "detail": "ok for all three periods" if not bad else
                    f"off in quarter(s) {bad}: e.g. {pbt[bad[0]]} - {tax[bad[0]]} vs {pat[bad[0]]}"})
    rev, oi, ti = L.get("revenue_from_operations"), L.get("other_income"), L.get("total_income")
    if rev and oi and ti and len(rev) == len(oi) == len(ti) == 3:
        bad = [i for i in range(3) if not _close(rev[i] + oi[i], ti[i], 0.005, 0.6)]
        out.append({"name": "revenue + other income = total income", "ok": not bad,
                    "detail": "ok" if not bad else f"off in quarter(s) {bad}"})
    # Independent source: screener's quarterly table, same basis only.
    if screener_q and pe and ex.get("unit") in UNIT_TO_CR and screener_basis == ex.get("basis") \
            and period_type(ex) == "quarter":
        k = UNIT_TO_CR[ex["unit"]]
        sq = screener_q.get(pe[0]) or {}
        pairs = [("revenue", (L.get("interest_earned") if bank else net_revenue(L))), ("pat", pat)]
        for name, vals in pairs:
            if vals and sq.get(name) is not None and len(vals) == 3:
                ours, theirs = vals[0] * k, sq[name]
                out.append({"name": f"{name} matches screener", "ok": _close(ours, theirs, 0.03, 1.0),
                            "detail": f"filing {ours:,.1f} cr vs screener {theirs:,.1f} cr"})
    elif screener_q:
        out.append({"name": "screener cross-check", "ok": True,
                    "detail": f"skipped: filing basis {ex.get('basis')} vs screener {screener_basis}"})
    return out


def compute(ex: dict) -> dict:
    """All derived numbers, in Rs crore, computed here."""
    k = UNIT_TO_CR.get(ex.get("unit"), 1.0)
    L = {n: [v * k for v in vals] for n, vals in (ex.get("lines") or {}).items()
         if len(vals) == 3 and not n.endswith("_pct")}
    pct = {n: vals for n, vals in (ex.get("lines") or {}).items() if n.endswith("_pct")}
    m: dict[str, list[float]] = {}
    bank = ex.get("is_bank_or_nbfc_format")
    if bank:
        if "interest_earned" in L and "interest_expended" in L:
            m["net_interest_income"] = [a - b for a, b in zip(L["interest_earned"], L["interest_expended"])]
        for n in ("operating_profit_before_provisions", "provisions"):
            if n in L:
                m[n] = L[n]
    else:
        if "revenue_from_operations" in L:
            m["revenue"] = net_revenue(L)
        base = L.get("profit_before_exceptional_and_tax")
        if base is None and "profit_before_tax" in L:
            exc = L.get("exceptional_items", [0, 0, 0])
            base = [p - e for p, e in zip(L["profit_before_tax"], exc)]
        if base and "finance_costs" in L and "depreciation" in L:
            oi = L.get("other_income", [0, 0, 0])
            m["ebitda"] = [b + f + d - o for b, f, d, o in zip(base, L["finance_costs"], L["depreciation"], oi)]
    for n, key in (("profit_before_tax", "pbt"), ("profit_after_tax", "pat")):
        if n in L:
            m[key] = L[n]
    metrics = {}
    for name, (cur, prev, ya) in m.items():
        qoq, qn = fundamentals.growth_pct(cur, prev)
        yoy, yn = fundamentals.growth_pct(cur, ya)
        metrics[name] = {"value": round(cur, 2), "prev": round(prev, 2), "year_ago": round(ya, 2),
                         "qoq_pct": qoq, "qoq_note": qn, "yoy_pct": yoy, "yoy_note": yn}
    if "revenue" in m and m["revenue"][0]:
        for name in ("ebitda", "pat"):
            if name in m:
                cur = m[name][0] / m["revenue"][0] * 100
                ya = m[name][2] / m["revenue"][2] * 100 if m["revenue"][2] else None
                metrics[f"{name}_margin_pct"] = {"value": round(cur, 1),
                                                 "change_bps_yoy": round((cur - ya) * 100) if ya is not None else None}
    for n, vals in pct.items():
        metrics[n] = {"value": vals[0] if vals else None, "prev": vals[1] if len(vals) > 1 else None}
    if "ebitda" in metrics:
        metrics["ebitda"]["note"] = "derived: profit before exceptional items and tax + finance costs + depreciation - other income"
    if "revenue" in metrics and "excise_duty" in L:
        metrics["revenue"]["note"] = "net of excise duty"
    return metrics


def _cr(v: float) -> str:
    return f"Rs {v:,.0f} cr" if abs(v) >= 10 else f"Rs {v:,.2f} cr"


def _chg(m: dict) -> str:
    return f"{m['yoy_pct']:+.1f}% YoY" if m.get("yoy_pct") is not None else (m.get("yoy_note") or "no YoY")


def summary(card: dict, label: str) -> dict | None:
    """Headline + one-liner written by Python from a verified card, so the words can
    never disagree with the numbers."""
    if card.get("status") != "verified":
        return None
    m = card.get("metrics") or {}
    pe = (card.get("period_ends") or [None])[0]
    span = "Half-year" if card.get("period_type") == "half_year" else "Quarter"
    try:
        when = date.fromisoformat(pe).strftime("%d %b %Y")
    except (TypeError, ValueError):
        when = pe or ""
    top = "net_interest_income" if "net_interest_income" in m else "revenue"
    top_label = "NII" if top == "net_interest_income" else "revenue"
    parts = [f"{top_label} {_cr(m[top]['value'])} ({_chg(m[top])})"] if top in m else []
    if "ebitda" in m:
        parts.append(f"EBITDA {_cr(m['ebitda']['value'])} ({_chg(m['ebitda'])})")
    if "pat" in m:
        parts.append(f"PAT {_cr(m['pat']['value'])} ({_chg(m['pat'])})")
    one = f"{span} to {when}, {card.get('basis') or ''}: " + ", ".join(parts)
    if len(one) > 140 and len(parts) == 3:
        one = f"{span} to {when}, {card.get('basis') or ''}: " + ", ".join([parts[0], parts[2]])
    pat = m.get("pat")
    head = f"{label} results: PAT {_cr(pat['value'])}, {_chg(pat)}" if pat else f"{label} results for {when}"
    return {"headline": head[:70], "one_liner": one[:140], "method": "from verified results card", "problems": []}


def build(url: str, symbol: str | None = None, trusted: set[str] | frozenset = frozenset()) -> dict:
    """Results card for one results filing."""
    t = documents.get_text(url, trusted=trusted)
    idx, basis_hint = find_result_pages(t["pages"])
    card: dict = {"type": "results", "status": "failed", "source_url": url, "pages": [i + 1 for i in idx],
                  "basis_hint": basis_hint, "attempts": []}
    if not idx:
        # Scanned filings have no text layer to search. Short ones go whole to the
        # model, which reads page images directly.
        if t["page_count"] <= SCANNED_MAX_PAGES:
            idx = list(range(t["page_count"]))
            card["pages"] = "all (no text layer to locate the table)"
        else:
            card["reason"] = "no results table found in the filing"
            return card
    pdf = mini_pdf(t["path"], idx)
    sq, sbasis = None, None
    if symbol:
        try:
            f = fundamentals.get_fundamentals(symbol).data
            sq, sbasis = f["quarterly"], f["basis"]
        except Exception:  # noqa: BLE001
            pass
    r = llm.router()
    for tier in ("lite", "flash"):
        res = r.complete("results_extract", "Extract the quarterly results statement on these pages.",
                         system=SYSTEM, tier=tier, schema=SCHEMA, pdf=pdf, max_tokens=4000)
        if not res or not isinstance(res.data, dict):
            card["attempts"].append({"tier": tier, "model": res.model if res else None, "ok": False,
                                     "why": "no answer" if not res else "not JSON"})
            continue
        ex = reorder(res.data)
        checks = check(ex, sq, sbasis)
        if ex.get("reordered_columns"):
            checks.append({"name": "columns re-ordered by date", "ok": True,
                           "detail": "the statement printed periods in a non-standard order"})
        ok = all(c["ok"] for c in checks)
        card["attempts"].append({"tier": tier, "model": res.model, "ok": ok, "cached": res.cached,
                                 "failed_checks": [c["name"] for c in checks if not c["ok"]]})
        pt = period_type(ex)
        card.update({"period_type": pt, "compare_label": "vs previous half-year" if pt == "half_year" else "QoQ",
                     "basis": ex.get("basis"), "unit_in_filing": ex.get("unit"), "units": "Rs crore",
                     "period_ends": ex.get("period_ends"), "bank_format": ex.get("is_bank_or_nbfc_format"),
                     "checks": checks, "metrics": compute(ex), "model": res.model})
        if ok:
            card["status"] = "verified"
            return card
        card["status"] = "not_verified"
    if card["status"] == "failed":
        card["reason"] = "the model could not read the statement" if r.available else "LLM not available (offline)"
    return card
