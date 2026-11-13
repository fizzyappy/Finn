"""One-line summaries for material filings: headline <= 70 chars, one-liner <= 140.

Written by Gemini Flash-Lite from the filing's own text, then checked in Python:
- length limits;
- every number in the summary must appear in the filing (no invented figures);
- no praise words ("strong", "major", "significant"...) unless a number sits in
  the same clause;
- the subject's company is the filing's company (no cross-talk).
A failing summary is retried once with Gemini Flash; if it still fails, we fall
back to the cleaned exchange subject line, which is always true.
"""
from __future__ import annotations

import re

from .. import documents, llm

HEADLINE_MAX, ONE_LINER_MAX = 70, 140
ADJECTIVES = {"strong", "robust", "significant", "major", "huge", "impressive", "substantial", "remarkable",
              "massive", "healthy", "solid", "stellar", "sharp", "steep", "excellent", "good", "great", "big",
              "notable", "strategic", "important", "landmark", "marquee", "prestigious", "best", "biggest",
              "largest", "highest"}

SYSTEM = (
    "You write for a busy equity investor. From the filing text, write a headline (at most 65 characters) and a "
    "one-line summary (at most 130 characters) saying what happened: the action, the counterparty, the amount, the "
    "date. Use only facts and numbers that appear in the text, and the filing's own verbs (do not call an outlook "
    "revision an upgrade). No adjectives unless they come with an amount. No advice, no opinion, no speculation "
    "about the share price."
)
# Action words that change the meaning of a summary: if the summary uses one, the
# filing must contain it too (catches "upgrade" when the filing says "outlook revised").
ACTIONS = ("upgrad", "downgrad", "acqui", "merg", "demerg", "resign", "appoint", "default", "penalt", "fine",
           "approv", "reject", "terminat", "suspend", "withdraw", "cancel", "win", "won", "bag", "launch",
           "divest", "sell", "sold", "buyback", "split", "bonus", "dividend", "reaffirm")
SCHEMA = {
    "type": "object",
    "properties": {"headline": {"type": "string"}, "one_liner": {"type": "string"}},
    "required": ["headline", "one_liner"],
}

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm_num(s: str) -> str:
    s = s.replace(",", "")
    return s[:-2] if s.endswith(".0") else s


def numbers_in_source(summary: str, source: str) -> list[str]:
    """Numbers in the summary that do NOT appear in the source (should be empty)."""
    src = {_norm_num(n) for n in _NUM.findall(source)}
    src_text = source.replace(",", "")
    missing = []
    for n in _NUM.findall(summary):
        k = _norm_num(n)
        if k not in src and k not in src_text:
            missing.append(n)
    return missing


_DATE = re.compile(r"\b\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s*(\d{4})?|"
                   r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?,?\s*(\d{4})?|"
                   r"\b(19|20)\d{2}\b|\bq[1-4]\b|\bfy\s*'?\d{2,4}\b|\bh[12]\b", re.I)


def unsupported_adjectives(text: str) -> list[str]:
    """Praise words need an amount in the same clause; dates and periods don't count."""
    bad = []
    for clause in re.split(r"[,;.:()–—]|\s-\s", text):
        words = set(re.findall(r"[a-z]+", clause.lower()))
        hits = words & ADJECTIVES
        if hits and not re.search(r"\d", _DATE.sub(" ", clause)):
            bad.extend(sorted(hits))
    return bad


def unsupported_actions(text: str, source: str) -> list[str]:
    low, src = text.lower(), source.lower()
    return [a for a in ACTIONS if re.search(rf"\b{a}", low) and not re.search(rf"\b{a}", src)]


def validate(s: dict, source: str) -> list[str]:
    problems = []
    h, o = (s.get("headline") or "").strip(), (s.get("one_liner") or "").strip()
    if not h or len(h) > HEADLINE_MAX:
        problems.append(f"headline length {len(h)}")
    if not o or len(o) > ONE_LINER_MAX:
        problems.append(f"one-liner length {len(o)}")
    for field_, txt in (("headline", h), ("one-liner", o)):
        miss = numbers_in_source(txt, source)
        if miss:
            problems.append(f"{field_} has numbers not in the filing: {miss}")
        adj = unsupported_adjectives(txt)
        if adj:
            problems.append(f"{field_} has adjectives without numbers: {adj}")
        act = unsupported_actions(txt, source)
        if act:
            problems.append(f"{field_} uses actions the filing does not: {act}")
    return problems


def clean_subject(subject: str) -> str:
    s = re.sub(r"^(announcement|intimation|disclosure)\s+under\s+regulation\s+\d+\s*(\(\w+\))?\s*(of .{0,40}?regulations?,? \d{4})?\s*[-:]?\s*",
               "", subject or "", flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" -:")
    return (s[:HEADLINE_MAX - 1] + "…") if len(s) > HEADLINE_MAX else s


def source_text(f: dict, trusted: set[str] | frozenset = frozenset(), max_chars: int = 6000) -> str:
    """The filing's own words: subject + first pages of the PDF (screener's detail line is not used)."""
    text = f"Subject: {f.get('subject') or ''}\n"
    if f.get("url"):
        try:
            t = documents.get_text(f["url"], trusted=trusted)
            text += "\n".join(t["pages"][:3])
        except Exception:  # noqa: BLE001
            pass
    return text[:max_chars]


_AGENCY = r"(ICRA|CRISIL|CARE|IND|India Ratings|BWR|Brickwork|ACUITE|Acuite|Infomerics|Fitch|S&P|Moody'?s)"
_RATING = re.compile(_AGENCY + r"\s*\]?\s*([A-D]{1,3}[+-]?\d?)\s*(?:/\s*(Stable|Positive|Negative|Developing))?\s*"
                     r"\(([^)]{3,160})\)", re.I)
_OUTLOOK = re.compile(r"outlook\w*\s+revised\s+to\s+['‘’\"]?(\w+)['‘’\"]?\s+from\s+['‘’\"]?(\w+)", re.I)
_DIVIDEND = re.compile(r"\b(interim|final|special)\s+dividend\s+of\s+(?:rs\.?|₹|inr)\s*([\d.]+)\s*(?:/-)?\s*per\s+(?:equity\s+)?share",
                       re.I)
_RECORD = re.compile(r"record date[^.]{0,60}?(\d{1,2}(?:st|nd|rd|th)?[\s-]+\w+[\s,-]+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}[./-]\d{1,2}[./-]\d{4})",
                     re.I)


def template(f: dict, src: str, category: str | None = None) -> dict | None:
    """Rules before LLM: fixed-format filings get a deterministic summary built from
    the filing's own words (no model, nothing to hallucinate). Each template only
    runs for its own category (a results filing also mentions its dividend)."""
    flat = re.sub(r"\s+", " ", src)
    m = _RATING.search(flat) if category in (None, "credit_rating") else None
    if m and re.search(r"rating", flat, re.I):
        agency, grade, outlook, action = m.group(1), m.group(2), m.group(3), m.group(4).strip()
        verb = "upgraded" if re.match(r"upgrad", action, re.I) else "downgraded" if re.match(r"downgrad", action, re.I) \
            else "reaffirmed" if re.match(r"reaffirm", action, re.I) else "assigned" if re.match(r"assign", action, re.I) else action
        o = _OUTLOOK.search(action)
        h = f"{agency} {grade} {verb}" + (f"; outlook {o.group(2)} to {o.group(1)}" if o else f", outlook {outlook}" if outlook else "")
        amt = re.search(r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)\s*(crores?|cr\b)", flat, re.I)
        one = h + (f" (Rs {amt.group(1)} crore facilities)" if amt else "")
        return {"headline": h[:HEADLINE_MAX], "one_liner": one[:ONE_LINER_MAX], "method": "template (credit rating)"}
    d = _DIVIDEND.search(flat) if category in (None, "dividend") else None
    if d:
        rd = _RECORD.search(flat)
        h = f"{d.group(1).title()} dividend of Rs {d.group(2)} per share"
        one = h + (f"; record date {rd.group(1)}" if rd else "")
        return {"headline": h[:HEADLINE_MAX], "one_liner": one[:ONE_LINER_MAX], "method": "template (dividend)"}
    return None


def repair(s: dict, src: str) -> dict | None:
    """Fix only what can be fixed by deleting: unsupported praise words, and a few
    characters over the limit (cut at a word boundary). Deleting cannot add a claim."""
    out = {}
    for key, limit in (("headline", HEADLINE_MAX), ("one_liner", ONE_LINER_MAX)):
        txt = (s.get(key) or "").strip()
        for adj in set(unsupported_adjectives(txt)):
            txt = re.sub(rf"\b{adj}\b\s*", "", txt, flags=re.I)
        txt = re.sub(r"\s{2,}", " ", txt).strip()
        if len(txt) > limit:
            txt = txt[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-") + "…"
        out[key] = txt
    return out if not validate(out, src) else None


def summarize(f: dict, trusted: set[str] | frozenset = frozenset(), category: str | None = None) -> dict:
    src = source_text(f, trusted)
    tpl = template(f, src, category)
    if tpl and not validate(tpl, src):
        return {**tpl, "problems": []}
    fallback = {"headline": clean_subject(f.get("subject") or ""), "one_liner": None, "method": "subject",
                "problems": []}
    r = llm.router()
    if not r.available:
        return fallback
    prompt = f"Company: {f.get('company') or f.get('symbol') or ''}\n\n{src}"
    problems_all = []
    for tier in ("lite", "flash"):
        res = r.complete("summarize", prompt, system=SYSTEM, tier=tier, schema=SCHEMA, max_tokens=600)
        if not res or not isinstance(res.data, dict):
            problems_all.append(f"{tier}: no answer")
            continue
        problems = validate(res.data, src)
        if not problems:
            return {"headline": res.data["headline"].strip(), "one_liner": res.data["one_liner"].strip(),
                    "method": f"llm ({res.model})", "problems": problems_all}
        problems_all.append(f"{tier}: " + "; ".join(problems))
        fixed = repair(res.data, src)
        if fixed:
            return {**fixed, "method": f"llm ({res.model}) + repaired", "problems": problems_all}
    return {**fallback, "problems": problems_all}
