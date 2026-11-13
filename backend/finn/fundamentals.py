"""Standardised financial statements and headline results, for any company.

All arithmetic (growth, margins) happens here in Python. Nothing downstream,
least of all an LLM, recomputes these numbers; it may only quote them.

Banks and NBFCs report differently (no "Sales"/"Operating Profit"; they have
"Revenue", "Financing Profit", NPAs, deposits). We detect that from the row
labels themselves, never from a list of company names.
"""
from __future__ import annotations

import re
from datetime import date

from . import screener
from .store import Fetched
from .symbols import resolve

# screener row label (lower-case) -> canonical metric name
ROW_MAP = {
    # P&L (quarterly and annual)
    "sales": "revenue", "revenue": "revenue",
    "expenses": "expenses", "operating profit": "ebitda", "opm %": "ebitda_margin_pct",
    "financing profit": "financing_profit", "financing margin %": "financing_margin_pct",
    "other income": "other_income", "interest": "interest", "depreciation": "depreciation",
    "profit before tax": "pbt", "tax %": "tax_pct", "net profit": "pat", "eps in rs": "eps",
    "dividend payout %": "dividend_payout_pct",
    "gross npa %": "gross_npa_pct", "net npa %": "net_npa_pct",
    # balance sheet
    "equity capital": "equity_capital", "reserves": "reserves", "borrowings": "borrowings",
    "borrowing": "borrowings", "deposits": "deposits", "other liabilities": "other_liabilities",
    "total liabilities": "total_liabilities", "fixed assets": "fixed_assets", "cwip": "cwip",
    "investments": "investments", "other assets": "other_assets", "total assets": "total_assets",
    # cash flow
    "cash from operating activity": "cfo", "cash from investing activity": "cfi",
    "cash from financing activity": "cff", "net cash flow": "net_cash_flow",
    "free cash flow": "fcf", "cfo/ebitda": "cfo_to_ebitda_pct",
    # ratios
    "debtor days": "debtor_days", "inventory days": "inventory_days", "days payable": "payable_days",
    "cash conversion cycle": "ccc_days", "working capital days": "wc_days",
    "roce %": "roce_pct", "roe %": "roe_pct",
    # shareholding
    "promoters": "promoters_pct", "fiis": "fii_pct", "diis": "dii_pct",
    "government": "govt_pct", "public": "public_pct", "no. of shareholders": "shareholders",
}


def is_lender(tables: dict) -> bool:
    rows = {r.lower() for r in (tables.get("quarters") or {}).get("rows", {})}
    return "financing profit" in rows or "gross npa %" in rows


def canonical(table: dict | None) -> dict[str, dict[str, float | None]]:
    """{period_end: {metric: value}} for one screener table. Unknown rows keep their label."""
    if not table:
        return {}
    out: dict[str, dict] = {}
    cols = table["columns"]
    for label, values in table["rows"].items():
        key = ROW_MAP.get(label.lower(), label)
        for col, v in zip(cols, values):
            pe = col["period_end"] or col["label"]          # TTM column has no date
            out.setdefault(pe, {})[key] = v
    return dict(sorted(out.items()))


def get_fundamentals(ticker: str, refresh: bool = False) -> Fetched:
    inst = resolve(ticker)
    page = screener.company(inst.screener_key, refresh=refresh)
    d = page.data
    t = d["tables"]
    data = {
        "instrument": inst.to_dict(),
        "name": d["name"], "basis": d["view"], "units": d["units"], "source_url": d["url"],
        "lender": is_lender(t),
        "top_ratios": d["top_ratios"],
        "quarterly": canonical(t.get("quarters")),
        "annual": canonical(t.get("profit_loss")),
        "balance_sheet": canonical(t.get("balance_sheet")),
        "cash_flow": canonical(t.get("cash_flow")),
        "ratios": canonical(t.get("ratios")),
        "shareholding": canonical(t.get("shareholding")),
        "quarter_pdfs": d["quarter_pdfs"],
        "documents": d["documents"],
        "about": d["about"],
    }
    return Fetched(data, page.source, page.fetched_at, page.stale, page.error)


def growth_pct(cur: float | None, base: float | None) -> tuple[float | None, str | None]:
    """Percent change, or (None, reason) when a percentage would mislead."""
    if cur is None or base is None:
        return None, "missing"
    if base == 0:
        return None, "base is zero"
    if base < 0 and cur >= 0:
        return None, "turned positive (from a loss)"
    if base < 0:
        return None, "loss in both periods"
    if cur < 0:
        return round((cur / base - 1) * 100, 1), "turned negative"
    return round((cur / base - 1) * 100, 1), None


def _year_ago(period_end: str) -> str:
    d = date.fromisoformat(period_end)
    y = d.replace(year=d.year - 1, day=1)
    # month end of the same month one year earlier
    nxt = y.replace(year=y.year + (y.month == 12), month=y.month % 12 + 1)
    return date.fromordinal(nxt.toordinal() - 1).isoformat()


_RESULTS = re.compile(r"financial results?|integrated filing \(financial\)|outcome of (the )?board meeting", re.I)
_NOT_RESULTS = re.compile(r"newspaper|publication|intimation|trading window|prior intimation|record date", re.I)


def results_document(ticker: str) -> dict | None:
    """The best primary document for the latest results, in order of preference:
    1. the results filing itself (from the company's recent filings / RSS store);
    2. the latest investor presentation (concall 'PPT', an exchange-hosted PDF).
    screener's own 'Raw PDF' links need a screener login, so they are not used."""
    from .filings import get_filings

    try:
        items = get_filings(ticker, days=100, use_apis=True)["items"]
    except Exception:  # noqa: BLE001
        items = []
    for it in items:
        text = f"{it.get('subject', '')} {it.get('category', '')}"
        if _RESULTS.search(text) and not _NOT_RESULTS.search(text) and it.get("url"):
            return {"kind": "results_filing", "url": it["url"], "title": it.get("subject"), "date": it.get("ts")}
    d = get_fundamentals(ticker).data
    quarters = [p for p in d["quarterly"] if p[:4].isdigit()]
    latest_q = quarters[-1] if quarters else "0000"
    for c in d["documents"]["concalls"]:
        # Only a presentation made after the latest quarter ended describes that quarter.
        if c.get("ppt") and (c.get("month_end") or "") > latest_q:
            return {"kind": "investor_presentation", "url": c["ppt"],
                    "title": f"Investor presentation ({c['period']})", "date": c.get("month_end")}
    return None


MIN_TRANSCRIPT_PAGES = 4


def latest_transcript(ticker: str) -> dict | None:
    """Newest *real* concall transcript, downloaded and checked.

    Some companies file only a one-page cover letter on the exchange ("the transcript
    is on our website"). Those are skipped, with a note of where they point, and the
    next-newest transcript is used. Returns the chosen candidate plus its text facts."""
    from . import documents

    trusted = document_links(ticker)
    skipped = []
    for c in transcript_candidates(ticker):
        try:
            t = documents.get_text(c["url"], trusted=trusted)
        except Exception as e:  # noqa: BLE001
            skipped.append({**c, "reason": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        if t["page_count"] < MIN_TRANSCRIPT_PAGES:
            links = list(dict.fromkeys(u.rstrip(".,;)") for u in re.findall(r"https?://\S+", " ".join(t["pages"]))))
            skipped.append({**c, "reason": f"cover letter ({t['page_count']} page)", "points_to": links[:3]})
            continue
        return {**c, "pages": t["page_count"], "chars": t["text_chars"], "skipped": skipped}
    return {"url": None, "skipped": skipped} if skipped else None


def transcript_candidates(ticker: str) -> list[dict]:
    """Transcript links, newest first, from screener's concall list and from the
    company's filings (a transcript filed this week can be missing from the concall list)."""
    from .filings import get_filings

    cands = []
    for c in get_fundamentals(ticker).data["documents"]["concalls"]:
        if c.get("transcript"):
            cands.append({"date": c.get("month_end") or "", "url": c["transcript"],
                          "title": f"Concall transcript ({c['period']})", "via": "concall list"})
    try:
        for it in get_filings(ticker, days=100)["items"]:
            if re.search(r"transcript", f"{it.get('subject', '')} {it.get('category', '')}", re.I) and it.get("url"):
                cands.append({"date": (it.get("ts") or "")[:10], "url": it["url"],
                              "title": it.get("subject"), "via": "filings"})
    except Exception:  # noqa: BLE001 - the concall list alone still works
        pass
    # month_end of a call month (e.g. 2026-11-30) can sort after a filing dated
    # 2026-11-10 for the same call; prefer the filing on a tie of year-month.
    cands.sort(key=lambda c: (c["date"][:7], c["via"] == "filings", c["date"]), reverse=True)
    seen, out = set(), []
    for c in cands:
        if c["url"] not in seen:
            seen.add(c["url"])
            out.append(c)
    return out


def document_links(ticker: str) -> set[str]:
    """Every primary-document link listed for this company (annual reports, concall
    transcripts and presentations). These may live on the company's own investor site."""
    docs = get_fundamentals(ticker).data["documents"]
    links = {a["url"] for a in docs["annual_reports"] if a.get("url")}
    for c in docs["concalls"]:
        links |= {c[k] for k in ("transcript", "ppt") if c.get(k)}
    return links


HEADLINE = ("revenue", "ebitda", "financing_profit", "other_income", "pbt", "pat", "eps")


def headline_results(ticker: str, refresh: bool = False) -> dict:
    """Latest quarter vs previous quarter and vs the same quarter a year earlier."""
    f = get_fundamentals(ticker, refresh=refresh)
    q = f.data["quarterly"]
    periods = [p for p in q if p[:4].isdigit()]
    if len(periods) < 2:
        raise LookupError("fewer than two quarters of results available")
    latest, prev = periods[-1], periods[-2]
    ya = _year_ago(latest)
    year_ago = ya if ya in q else None
    out = {
        "symbol": f.data["instrument"]["symbol"], "name": f.data["name"],
        "basis": f.data["basis"], "units": f.data["units"], "lender": f.data["lender"],
        "quarter_end": latest, "prev_quarter_end": prev, "year_ago_quarter_end": year_ago,
        "metrics": {}, "source": f.meta(),
    }
    for m in HEADLINE:
        cur = q[latest].get(m)
        if cur is None and m not in q[latest]:
            continue
        p = q[prev].get(m)
        y = q[year_ago].get(m) if year_ago else None
        qoq, qoq_note = growth_pct(cur, p)
        yoy, yoy_note = growth_pct(cur, y) if year_ago else (None, "no year-ago quarter")
        out["metrics"][m] = {"value": cur, "prev": p, "year_ago": y,
                             "qoq_pct": qoq, "qoq_note": qoq_note, "yoy_pct": yoy, "yoy_note": yoy_note}
    rev = q[latest].get("revenue")
    eb = q[latest].get("ebitda")
    pat = q[latest].get("pat")
    if rev:
        if eb is not None:
            out["metrics"]["ebitda_margin_pct"] = {"value": round(eb / rev * 100, 1)}
        if pat is not None:
            out["metrics"]["pat_margin_pct"] = {"value": round(pat / rev * 100, 1)}
    if f.data["lender"]:
        out["note"] = ("Lender: EBITDA does not apply. 'financing_profit' is screener's figure "
                       "after interest and provisions; judge on revenue, PBT, PAT and NPAs.")
        for m in ("gross_npa_pct", "net_npa_pct"):
            if q[latest].get(m) is not None:
                out["metrics"][m] = {"value": q[latest][m], "prev": q[prev].get(m)}
    return out
