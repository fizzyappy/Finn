"""People card: who joined or left, in what role, from when, why, and their background,
all taken from the filing itself (SEBI's Regulation 30 disclosure must include a
brief profile of an appointee and the reason for a change).

The model extracts; Python verifies. Every profile line must be found word for
word in the filing's text (page number recorded), or it is dropped. A person
whose name is not in the filing is dropped.
"""
from __future__ import annotations

import re

from .. import documents, llm

SYSTEM = (
    "You read Indian stock-exchange filings about changes in directors and senior management. For each person "
    "whose position changes, give their name, role, the kind of change, the effective date, the reason given, and "
    "up to 4 lines of their background copied WORD FOR WORD from the filing (each line one sentence or table cell, "
    "with the page number shown in [page N] markers). Do not paraphrase background lines. Use only the text given."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "people": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role": {"type": "string"},
                "change": {"type": "string", "enum": ["appointment", "reappointment", "resignation", "cessation",
                                                      "retirement", "redesignation", "other"]},
                "effective_date": {"type": "string"},
                "reason": {"type": "string"},
                "background": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"quote": {"type": "string"}, "page": {"type": "integer"}},
                    "required": ["quote", "page"]}},
            },
            "required": ["name", "role", "change", "effective_date", "reason", "background"]}},
    },
    "required": ["people"],
}


_PEOPLE_WORDS = re.compile(r"appoint|resign|cessation|director|\bdin\b|brief profile|profile|experience|"
                           r"qualification|designation|effective|retire|superannuat|key managerial", re.I)


def _paged(pages: list[str], max_chars: int = 16000) -> str:
    """The pages that talk about people (long outcome filings bury the annexure
    deep), in their original order, each marked with its page number."""
    ranked = sorted(range(len(pages)), key=lambda i: -len(_PEOPLE_WORDS.findall(pages[i])))
    chosen, used = {0}, len(pages[0]) if pages else 0
    for i in ranked:
        if i in chosen or not _PEOPLE_WORDS.search(pages[i]):
            continue
        if used + len(pages[i]) > max_chars:
            continue
        chosen.add(i)
        used += len(pages[i])
    return "\n".join(f"[page {i + 1}]\n{pages[i].strip()}\n" for i in sorted(chosen) if i < len(pages))


def verify_people(raw: list[dict], pages: list[str]) -> tuple[list[dict], int]:
    """Keep only what the filing actually says. Returns (people, dropped_line_count)."""
    kept, dropped = [], 0
    for p in raw:
        name = re.sub(r"^(mr|ms|mrs|dr|shri|smt)\.?\s+", "", (p.get("name") or "").strip(), flags=re.I)
        if not name or documents.find_quote(pages, name) is None:
            dropped += len(p.get("background") or []) + 1
            continue
        lines = []
        for b in p.get("background") or []:
            q = (b.get("quote") or "").strip()
            page = documents.find_quote(pages, q) if len(q) >= 12 else None
            if page is None:
                dropped += 1
                continue
            lines.append({"text": q, "page": page, "source": "filing"})
        kept.append({**p, "name": name, "background": lines})
    return kept, dropped


def build(url: str, trusted: set[str] | frozenset = frozenset()) -> dict:
    card: dict = {"type": "people", "status": "failed", "source_url": url, "people": []}
    try:
        t = documents.get_text(url, trusted=trusted)
    except Exception as e:  # noqa: BLE001
        card["reason"] = f"could not read the filing: {type(e).__name__}"
        return card
    if t["status"] != "ok":
        card["reason"] = "the filing has no text layer (scanned), so quotes cannot be verified"
        return card
    res = llm.router().complete("people_extract", _paged(t["pages"]), system=SYSTEM, tier="lite",
                                schema=SCHEMA, max_tokens=3000)
    if not res or not isinstance(res.data, dict):
        card["reason"] = "LLM not available" if not llm.router().available else "the model gave no usable answer"
        return card
    people, dropped = verify_people(res.data.get("people") or [], t["pages"])
    card.update({"status": "verified" if people else "not_verified", "people": people,
                 "dropped_unverified_lines": dropped, "model": res.model})
    return card


def headline(card: dict) -> str | None:
    """'Rakesh Sony appointed Additional Director (from 2026-11-13)' etc., from verified fields only."""
    if not card.get("people"):
        return None
    verbs = {"appointment": "appointed", "reappointment": "reappointed", "resignation": "resigns as",
             "cessation": "ceases to be", "retirement": "retires as", "redesignation": "redesignated as"}
    p = card["people"][0]
    v = verbs.get(p.get("change"), "change:")
    more = f" (+{len(card['people']) - 1} more)" if len(card["people"]) > 1 else ""
    eff = f", effective {p['effective_date']}" if p.get("effective_date") else ""
    return f"{p['name']} {v} {p.get('role') or ''}{eff}{more}".replace("  ", " ")[:140]
