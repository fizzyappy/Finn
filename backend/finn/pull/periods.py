"""Indian fiscal periods. FY runs April to March: FY27 = Apr 2026 - Mar 2027.
Q1 = Apr-Jun, Q2 = Jul-Sep, Q3 = Oct-Dec, Q4 = Jan-Mar. H1 = Q1+Q2, H2 = Q3+Q4.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date


def fy_of(d: date) -> int:
    """FY number (2027 for FY27) that contains date d."""
    return d.year + 1 if d.month >= 4 else d.year


def quarter_of(d: date) -> tuple[int, int]:
    return fy_of(d), ((d.month - 4) % 12) // 3 + 1


def month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def quarter_end(fy: int, q: int) -> date:
    m = {1: 6, 2: 9, 3: 12, 4: 3}[q]
    return month_end(fy - 1 if q < 4 else fy, m)


def quarters_of(fy: int, half: int | None = None) -> list[date]:
    qs = [quarter_end(fy, q) for q in range(1, 5)]
    return qs[:2] if half == 1 else qs[2:] if half == 2 else qs


def label(fy: int, q: int | None = None, half: int | None = None) -> str:
    y = f"FY{fy % 100:02d}"
    return f"Q{q}{y}" if q else f"H{half}{y}" if half else y


@dataclass(frozen=True)
class Horizon:
    kind: str                 # FY | H | Q | multi | open
    fy: int | None = None
    part: int | None = None   # quarter or half number
    end: date | None = None   # when it can be measured
    text: str = ""

    @property
    def label(self) -> str:
        if self.kind == "FY":
            return label(self.fy)
        if self.kind == "H":
            return label(self.fy, half=self.part)
        if self.kind == "Q":
            return label(self.fy, q=self.part)
        return self.text or self.kind


def discussed_quarter(call_date: date) -> tuple[int, int]:
    """A call is about the quarter that ended before it (an October call discusses Q2)."""
    m = call_date.month - 1 or 12
    y = call_date.year if call_date.month > 1 else call_date.year - 1
    return quarter_of(date(y, m, 1))


def resolve(text: str, call_date: date) -> Horizon:
    """'FY27', 'H2 FY27', 'Q3', 'this year', 'next year', 'by FY30', 'medium term' -> Horizon."""
    s = (text or "").lower().replace("’", "'").replace("‘", "'")
    fy_now, q_now = discussed_quarter(call_date)
    # In a Q4 call (April-May) "this year" means the new fiscal year.
    fy_this = fy_now + 1 if q_now == 4 else fy_now
    # A fiscal range names the year it ends in: "FY24-25" = FY25, "'26-'27" / "2026-27" = FY27.
    rng = re.search(r"(?:fy\s*|financial year\s*|fiscal\s*|\b)'?(\d{2}|\d{4})\s*[-–/]\s*'?(\d{2})\b(?!\s*%)", s)
    if rng and (re.search(r"fy|financial|fiscal|'", s[max(0, rng.start() - 15): rng.end()])):
        y = int(rng.group(2))
        fy = 2000 + y if y < 100 else y
        return Horizon("FY", fy, None, quarter_end(fy, 4), text)
    fy_all = [m for m in re.finditer(r"\b(?:q([1-4])\s*)?(?:h([12])\s*)?fy\s*'?(\d{2}|\d{4})\b", s)]
    # Several years named ("FY'23 and FY'24"): the promise runs to the last one.
    m = max(fy_all, key=lambda x: int(x.group(3)) % 100) if fy_all else \
        re.search(r"\b(?:fiscal|financial year)\s*(?:year\s*)?'?(\d{2}|\d{4})\b", s)
    if m:
        groups = m.groups()
        y = int(groups[-1])
        fy = 2000 + y if y < 100 else y
        q = int(groups[0]) if len(groups) == 3 and groups[0] else None
        h = int(groups[1]) if len(groups) == 3 and groups[1] else None
        if q:
            return Horizon("Q", fy, q, quarter_end(fy, q), text)
        if h:
            return Horizon("H", fy, h, quarters_of(fy, h)[-1], text)
        multi = re.search(r"\bby\b|\btill\b|\buntil\b", s) and fy - fy_this >= 2
        return Horizon("multi" if multi else "FY", fy, None, quarter_end(fy, 4), text)
    mo = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*['’]?\s*(\d{2}|\d{4})\b", s)
    if mo:
        y = int(mo.group(2))
        y = 2000 + y if y < 100 else y
        mnum = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(mo.group(1)) + 1
        fy, qn = quarter_of(date(y, mnum, 1))
        if qn == 4 and mnum == 3:
            return Horizon("FY", fy, None, quarter_end(fy, 4), text)
        return Horizon("Q", fy, qn, quarter_end(fy, qn), text)
    yrs = re.search(r"\b(?:over|next|in|within)\s+(?:the\s+)?(?:next\s+)?(two|three|four|five|six|seven|ten|\d+)\s*(?:-\s*\w+\s*)?years?\b", s)
    if yrs:
        words = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10}
        n = words.get(yrs.group(1), None) or int(yrs.group(1))
        fy = fy_this + n - 1
        return Horizon("multi", fy, None, quarter_end(fy, 4), text)
    q = re.search(r"\bq([1-4])\b", s)
    if q:
        qn = int(q.group(1))
        fy = fy_this if qn > q_now or q_now == 4 else fy_this + 1
        return Horizon("Q", fy, qn, quarter_end(fy, qn), text)
    if re.search(r"next quarter|coming quarter", s):
        fy, qn = (fy_now, q_now + 1) if q_now < 4 else (fy_now + 1, 1)
        return Horizon("Q", fy, qn, quarter_end(fy, qn), text)
    if re.search(r"second half|\bh2\b", s):
        return Horizon("H", fy_this, 2, quarters_of(fy_this, 2)[-1], text)
    if re.search(r"first half|\bh1\b", s):
        return Horizon("H", fy_this, 1, quarters_of(fy_this, 1)[-1], text)
    if re.search(r"next (fiscal|financial)? ?year|coming year|following year", s):
        return Horizon("FY", fy_this + 1, None, quarter_end(fy_this + 1, 4), text)
    if re.search(r"this (fiscal|financial)? ?year|current (fiscal|financial)? ?year|full[- ](fiscal |financial )?year|"
                 r"for the year|annual|\bthe year\b", s):
        return Horizon("FY", fy_this, None, quarter_end(fy_this, 4), text)
    y = re.search(r"\b(?:by|in|till|until)\s+(20\d{2})\b", s)
    if y:
        fy = int(y.group(1))
        return Horizon("multi", fy, None, quarter_end(fy, 4), text)
    return Horizon("open", None, None, None, text or "no date given")
