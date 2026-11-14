"""Business snapshot: what the company sells, by segment, from its latest annual report.

The pages holding the segment table are found by text; only those pages go to
Gemini Flash-Lite (as a small PDF) to read segment names and revenue for the two
years. Python checks that each segment name is on the page, converts units, and
compares the segment total with reported revenue before calling it verified; it
then computes the revenue mix and growth. If the report has no readable segment
table, the section says so instead of guessing.
"""
from __future__ import annotations

import re

from .. import documents, fundamentals, llm
from ..push.results_card import UNIT_TO_CR, mini_pdf

SEG = re.compile(r"segment(al)?\s+(revenue|information|results|reporting)|revenue\s+by\s+(segment|business)|operating segments",
                 re.I)
SYSTEM = (
    "You read the segment information table of an Indian company's annual report. Report each reportable segment's "
    "external revenue for the latest year and the previous year exactly as printed (no calculations), the unit, "
    "and whether the table is consolidated or standalone. Skip 'unallocated', 'eliminations' and totals."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "basis": {"type": "string", "enum": ["consolidated", "standalone"]},
        "unit": {"type": "string", "enum": list(UNIT_TO_CR)},
        "latest_year_end": {"type": "string", "description": "YYYY-MM-DD"},
        "segments": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "revenue_latest": {"type": "number"}, "revenue_previous": {"type": "number"}},
            "required": ["name", "revenue_latest"]}},
    },
    "required": ["basis", "unit", "latest_year_end", "segments"],
}


def find_segment_pages(pages: list[str], limit: int = 2) -> list[int]:
    scored = []
    for i, p in enumerate(pages):
        if not SEG.search(p):
            continue
        nums = len(re.findall(r"\d[\d,]*\.\d+|\d{1,3}(?:,\d{2,3})+", p))
        if nums < 12:
            continue
        score = len(SEG.findall(p)) * 5 + min(nums, 80) + (10 if re.search(r"consolidated", p, re.I) else 0)
        scored.append((score, i))
    return sorted(i for _, i in sorted(scored, reverse=True)[:limit])


def build(ticker: str) -> dict:
    f = fundamentals.get_fundamentals(ticker).data
    ars = [a for a in f["documents"]["annual_reports"] if a.get("url")]
    out: dict = {"status": "not_found", "segments": []}
    if not ars:
        out["note"] = "no annual report link found"
        return out
    ar = ars[0]
    out["source"] = {"title": ar["title"], "url": ar["url"], "year": ar.get("year")}
    try:
        t = documents.get_text(ar["url"], trusted=fundamentals.document_links(ticker))
    except Exception as e:  # noqa: BLE001
        out["note"] = f"could not read the annual report: {type(e).__name__}: {str(e)[:100]}"
        return out
    idx = find_segment_pages(t["pages"])
    if not idx:
        out["note"] = "the annual report has no readable segment revenue table (single-segment company or scanned pages)"
        return out
    out["pages"] = [i + 1 for i in idx]
    res = llm.router().complete("segments", "Read the segment revenue table on these pages.", system=SYSTEM,
                                tier="lite", schema=SCHEMA, pdf=mini_pdf(t["path"], idx), max_tokens=2000)
    if not res or not isinstance(res.data, dict):
        out["status"] = "ai_unavailable"
        return out
    k = UNIT_TO_CR.get(res.data.get("unit"), None)
    page_text = [t["pages"][i] for i in idx]
    segs, dropped = [], []
    for s in res.data.get("segments") or []:
        name = (s.get("name") or "").strip()
        if not name or documents.find_quote(page_text, name) is None or k is None:
            dropped.append(name)
            continue
        cur = s["revenue_latest"] * k
        prev = s.get("revenue_previous")
        segs.append({"name": name, "revenue_cr": round(cur, 1),
                     "growth_pct": fundamentals.growth_pct(cur, prev * k if prev is not None else None)[0]})
    total = sum(s["revenue_cr"] for s in segs)
    for s in segs:
        s["mix_pct"] = round(s["revenue_cr"] / total * 100, 1) if total else None
    ye = res.data.get("latest_year_end") or ""
    reported = (f["annual"].get(ye) or {}).get("revenue")
    gap = round((total / reported - 1) * 100, 1) if reported and total else None
    same_basis = res.data.get("basis") == f["basis"]
    out.update({
        "segments": sorted(segs, key=lambda s: -s["revenue_cr"]), "basis": res.data.get("basis"), "year_end": ye,
        "segment_total_cr": round(total, 1), "reported_revenue_cr": reported, "gap_pct": gap, "dropped_names": dropped,
        "status": "verified" if segs and gap is not None and same_basis and abs(gap) <= 7 else ("unverified" if segs else "not_found"),
        "check": (f"segments add up to {total:,.0f} cr vs reported revenue {reported:,.0f} cr ({gap:+.1f}%)"
                  if gap is not None else "could not match the year to reported revenue")
                 + ("" if same_basis else f"; table is {res.data.get('basis')}, statements are {f['basis']}"),
        "model": res.model,
    })
    return out
