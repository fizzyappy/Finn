"""Two-stage classifier: rules first, Gemini Flash-Lite only for low-confidence items.

Stage 1 (free, deterministic): ordered rules over the subject, the exchange's own
category, the detail line and the attachment file name.
Stage 2 (only when no rule fired, only the generic press-release rule fired, or
the subject says nothing, e.g. BSE's "Please refer enclosed"): the LLM reads the
first page of the filing PDF and must answer in strict JSON from the closed list
of categories. Cached by content hash, so a filing is never classified twice.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from .. import documents, llm
from .taxonomy import CATEGORIES, CATEGORY_BASE, RULES, Classification

SYSTEM = (
    "You classify Indian listed-company stock-exchange filings for an investor. Pick exactly one category: "
    + ", ".join(CATEGORIES) + ". Meanings: results=quarterly/annual financial results; M&A=acquisition, merger, "
    "demerger, JV, stake sale; fund_raise=QIP, rights, preferential, warrants, buyback, debt issue; "
    "management_change=directors or senior management join/leave; litigation=lawsuits, regulatory orders, penalties, "
    "insolvency; insider_trading=insider/promoter dealing disclosures; earnings_call=call notice, transcript, recording; "
    "investor_meetings=analyst/fund meetings; credit_rating; dividend; bonus_split; capex=new plant, capacity, "
    "facility; press_release=orders, business updates, clarifications, other news; postal_ballot; agm_egm; pledging; "
    "unclassified=routine compliance paperwork. Use only the text given."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "subtype": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["category", "subtype", "confidence", "reason"],
}


def attachment_name(url: str | None) -> str:
    if not url:
        return ""
    name = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    # exchange attachment names are often uuids: only keep ones made of words
    name = re.sub(r"\.pdf$", "", name, flags=re.I)
    return "" if re.fullmatch(r"[0-9a-f\-]{20,}", name, re.I) else re.sub(r"[_\-]+", " ", name)


def rule_classify(f: dict) -> tuple[Classification, bool]:
    """(classification, needs_llm)."""
    subject = f"{f.get('category') or ''} | {f.get('subject') or ''}"
    blob = " ".join(str(f.get(k) or "") for k in ("subject", "category", "detail")) + " " + attachment_name(f.get("url"))
    for rule in RULES:
        if rule.matches(subject, blob):
            generic = rule.subtype == "general"
            conf = 0.55 if generic else (0.95 if rule.subject and rule.text else 0.85)
            c = Classification(rule.category, rule.subtype, rule.base, conf, "rule", rule.routine, rule.card,
                               [rule.subtype])
            return c, generic
    return Classification("unclassified", "unknown", CATEGORY_BASE["unclassified"], 0.3, "default", True, "none"), True


def first_page_text(url: str | None, max_chars: int = 3000) -> str:
    if not url:
        return ""
    try:
        t = documents.get_text(url)
    except Exception:  # noqa: BLE001 - classification still works on the subject
        return ""
    return (t["pages"][0] if t["pages"] else "")[:max_chars]


def classify(f: dict, use_llm: bool = True) -> Classification:
    c, needs_llm = rule_classify(f)
    if not (needs_llm and use_llm and llm.router().available):
        return c
    page = first_page_text(f.get("url"))
    prompt = (f"Company: {f.get('company') or f.get('symbol') or ''}\nSubject: {f.get('subject') or ''}\n"
              f"Exchange category: {f.get('category') or ''}\nFirst page of the filing:\n{page or '(not available)'}")
    res = llm.router().complete("classify", prompt, system=SYSTEM, tier="lite", schema=SCHEMA, max_tokens=400)
    if not res or not isinstance(res.data, dict) or res.data.get("category") not in CATEGORIES:
        return c
    cat = res.data["category"]
    conf = max(0.0, min(float(res.data.get("confidence") or 0.6), 0.9))
    # Re-run the rules restricted to the LLM's category to recover a subtype and base.
    blob = f"{f.get('subject') or ''} {page[:1500]}"
    for rule in RULES:
        if rule.category == cat and rule.subtype != "general" and rule.matches(f"{f.get('subject') or ''}", blob):
            return Classification(cat, rule.subtype, rule.base, conf, "llm", rule.routine, rule.card,
                                  [f"llm: {res.data.get('reason', '')[:120]}"])
    card = "people" if cat == "management_change" else "results" if cat == "results" else "summary"
    return Classification(cat, res.data.get("subtype") or "llm", CATEGORY_BASE[cat], conf, "llm",
                          CATEGORY_BASE[cat] < 0.15, card, [f"llm: {res.data.get('reason', '')[:120]}"])
