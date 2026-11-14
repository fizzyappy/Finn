"""Concall transcripts: find the company's real transcripts, split them into speaker
turns (with page numbers), tell management from analysts, and pair each analyst
question with management's answer.

Layouts differ by company ("Name:" on the line, or the name alone on its own
line), so speakers are found from the document itself: short Title-Case lines or
"Name:" prefixes that recur, excluding running headers/footers.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

from .. import documents, fundamentals

MIN_PAGES = fundamentals.MIN_TRANSCRIPT_PAGES

COLON_SPEAKER = re.compile(r"^\s*(Moderator|[A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,4})\s*:\s*(\S.*)$")
NAME_LINE = re.compile(r"^\s*([A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){1,4})\s*$")
INTRO = re.compile(r"(?:question|questions)\s+(?:is|comes|come)?\s*(?:from|on)\s+(?:the\s+line\s+of\s+)?"
                   r"(?:Mr\.?\s+|Ms\.?\s+|Mrs\.?\s+)?([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3})", re.I)
NOT_NAMES = {"Page", "Thank You", "Thanks", "Good Morning", "Good Evening", "Good Afternoon", "Ladies And Gentlemen",
             "Safe Harbour", "Disclaimer", "Question And Answer", "Questions And Answers", "Opening Remarks",
             # document labels that look like "Name:" lines
             "Sensitivity", "Classification", "Confidential", "Note", "Notes", "Source", "Date", "Subject", "Ref",
             "Time", "Venue", "Website", "Email", "Tel", "Phone", "Fax", "Cin", "Registered Office", "Corporate Office"}


@dataclass
class Turn:
    speaker: str
    role: str            # management | analyst | moderator
    page: int            # 1-based page where the turn starts
    text: str
    section: str = "remarks"   # remarks | qa


@dataclass
class Transcript:
    url: str
    date: str            # call month end / filing date, YYYY-MM-DD
    title: str
    pages: list[str]
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("pages")
        return d


def _boilerplate(pages: list[str]) -> set[str]:
    """Running headers/footers: lines in the top or bottom three lines of many pages
    (company name, 'Page x of y'). Mid-page lines never count, so a speaker who talks
    on every page is not mistaken for a header."""
    c: Counter = Counter()
    for p in pages:
        lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
        edge = lines[:3] + lines[-3:]
        for ln in {re.sub(r"\d+", "#", x) for x in edge}:
            c[ln] += 1
    return {ln for ln, n in c.items() if n >= max(3, len(pages) * 0.4)}


def split_turns(pages: list[str]) -> list[Turn]:
    boiler = _boilerplate(pages)
    lines: list[tuple[int, str]] = []
    for pno, p in enumerate(pages, 1):
        for ln in p.splitlines():
            s = ln.strip()
            if s and re.sub(r"\d+", "#", s) not in boiler:
                lines.append((pno, s))
    # Candidate speaker names: "Name:" prefixes, or Name-only lines that recur.
    standalone = Counter(m.group(1).strip() for _, s in lines if (m := NAME_LINE.match(s)))
    colon = Counter(m.group(1).strip() for _, s in lines if (m := COLON_SPEAKER.match(s)))
    # Names that speak once (an analyst with one question) count if the moderator
    # introduced them or the participant list names them.
    full = " ".join(s for _, s in lines)
    known = {m.group(1).strip() for m in INTRO.finditer(full)} | {
        m.group(1).strip() for p in pages[:3] for ln in p.splitlines() if (m := NAME_LINE.match(ln))}

    def accept(n: str, k: int) -> bool:
        if n in NOT_NAMES or len(n) > 40:
            return False
        return k >= 2 or (k == 1 and len(n.split()) >= 2 and any(_same_person(n, x) for x in known))
    speakers = {n for n, k in colon.items() if accept(n, k)}
    if len(speakers) < 2:
        speakers |= {n for n, k in standalone.items() if accept(n, k)}
    turns: list[dict] = []
    for pno, s in lines:
        m = COLON_SPEAKER.match(s)
        if m and m.group(1).strip() in speakers:
            turns.append({"speaker": m.group(1).strip(), "page": pno, "text": m.group(2).strip()})
            continue
        m2 = NAME_LINE.match(s)
        if m2 and m2.group(1).strip() in speakers:
            turns.append({"speaker": m2.group(1).strip(), "page": pno, "text": ""})
            continue
        if turns:
            turns[-1]["text"] += (" " if turns[-1]["text"] else "") + s
    # Speech has sentences; participant lists ("Name / Firm") do not.
    turns = [t for t in turns if re.search(r"[.?!]", t["text"]) or len(t["text"].split()) >= 15]
    return assign_roles(turns, pages)


MGMT_TITLE = re.compile(r"\b(ceo|cfo|coo|cto|chief|managing director|director|chairman|chairperson|president|"
                        r"head|officer|founder|whole[- ]time|executive|treasurer|investor relations|company secretary)\b", re.I)
FIRM = re.compile(r"\b(securities|capital|research|equities|equity|broking|brokers|advisors|advisers|asset management|"
                  r"investments?|partners|fund|amc|insurance|ventures|holdings|limited|ltd|llp|inc|plc|"
                  r"times|mint|express|herald|businessline|fortune|businessworld|reuters|bloomberg|cnbc|moneycontrol)\b", re.I)


def roles_from_header(pages: list[str], names: set[str]) -> dict[str, str]:
    """Participant lists on the first pages say who is who: a title (CEO, CFO, Head...)
    means management; a firm or publication name means analyst / journalist."""
    head = re.sub(r"\s+", " ", " ".join(pages[:3]))
    out = {}
    others = [re.escape(x) for x in names if len(x) > 3]
    for n in names:
        for m in re.finditer(re.escape(n), head):
            after = head[m.end(): m.end() + 50]
            if others:
                after = re.split(r"\b(?:" + "|".join(x for x in others if x != re.escape(n)) + r")\b", after)[0]
            t, f = MGMT_TITLE.search(after), FIRM.search(after)
            if t and (not f or t.start() < f.start()):
                out[n] = "management"
                break
            if f:
                out[n] = "analyst"
                break
    return out


def _same_person(a: str, b: str) -> bool:
    import difflib

    a, b = a.lower(), b.lower()
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def assign_roles(turns: list[dict], pages: list[str] | None = None) -> list[Turn]:
    # Whoever keeps introducing questioners is acting as the moderator (an IR head often does).
    intro_count: Counter = Counter()
    for t in turns:
        if INTRO.search(t["text"]) and len(t["text"].split()) < 60:
            intro_count[t["speaker"]] += 1
    acting_moderators = {s for s, k in intro_count.items() if k >= 3}
    introduced = set()
    for t in turns:
        if t["speaker"].lower().startswith("moderator") or t["speaker"] in acting_moderators:
            for m in INTRO.finditer(t["text"]):
                introduced.add(m.group(1).strip().lower())
    header = roles_from_header(pages or [], {t["speaker"] for t in turns}) if pages else {}
    stats: dict[str, list[int]] = {}
    for t in turns:
        st = stats.setdefault(t["speaker"], [0, 0, 0])
        st[0] += 1
        st[1] += t["text"].count("?")
        st[2] += len(t["text"].split())

    def role(name: str) -> str:
        if name.lower().startswith("moderator") or name in acting_moderators:
            return "moderator"
        if any(_same_person(name, i) for i in introduced):
            return "analyst"
        if name in header:
            return header[name]
        if name.lower() in ("management", "company"):
            return "management"
        n, q, words = stats[name]
        # Analysts mostly ask; management mostly talks at length.
        return "analyst" if q / n >= 0.5 and words / n < 150 else "management"

    out, in_qa = [], False
    for t in turns:
        r = role(t["speaker"])
        if r == "analyst":
            in_qa = True
        out.append(Turn(t["speaker"], r, t["page"], re.sub(r"\s+", " ", t["text"]).strip(), "qa" if in_qa else "remarks"))
    return out


def qa_pairs(turns: list[Turn]) -> list[dict]:
    """Each analyst question (consecutive analyst turns) with the management answer
    that follows (consecutive management turns), until the next analyst or moderator."""
    pairs, i = [], 0
    while i < len(turns):
        if turns[i].role != "analyst":
            i += 1
            continue
        q = [turns[i]]
        i += 1
        while i < len(turns) and turns[i].role == "analyst":
            q.append(turns[i])
            i += 1
        a = []
        while i < len(turns) and turns[i].role == "management":
            a.append(turns[i])
            i += 1
        if a:
            pairs.append({"analyst": q[0].speaker, "question": " ".join(t.text for t in q), "q_page": q[0].page,
                          "answer": " ".join(t.text for t in a), "a_page": a[0].page,
                          "answered_by": sorted({t.speaker for t in a})})
    return pairs


def load(ticker: str, n: int = 5) -> tuple[list[Transcript], list[dict]]:
    """The latest `n` real transcripts (cover letters skipped), newest first, plus notes on skips."""
    trusted = fundamentals.document_links(ticker)
    out, notes, seen_months = [], [], set()
    for c in fundamentals.transcript_candidates(ticker):
        if len(out) >= n:
            break
        month = (c.get("date") or "")[:7]
        if month in seen_months:
            continue
        try:
            t = documents.get_text(c["url"], trusted=trusted)
        except Exception as e:  # noqa: BLE001
            notes.append({"url": c["url"], "date": c.get("date"), "skipped": f"{type(e).__name__}: {str(e)[:100]}"})
            continue
        if t["page_count"] < MIN_PAGES or t["status"] != "ok":
            notes.append({"url": c["url"], "date": c.get("date"),
                          "skipped": "cover letter or scanned" if t["status"] == "ok" else t["status"]})
            continue
        tr = Transcript(c["url"], c.get("date") or "", c.get("title") or "", t["pages"], split_turns(t["pages"]))
        if sum(1 for x in tr.turns if x.role == "management") < 3:
            notes.append({"url": c["url"], "date": c.get("date"), "skipped": "could not find speaker turns"})
            continue
        seen_months.add(month)
        out.append(tr)
    return out, notes
