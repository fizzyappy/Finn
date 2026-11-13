"""screener.in company pages: standardised statements + links to primary documents.

One page per company gives us (a) ~12 quarters and ~12 years of P&L, balance
sheet, cash flow and ratios, (b) the BSE scrip code, and (c) links to the
company's annual reports, concall transcripts and results filings, all hosted on
BSE/NSE (primary documents). We fetch the page once, cache it 24h, parse
everything.

Every table column carries its exact period-end date (data-date-key, e.g.
2026-09-30), so a quarter is matched to the same quarter a year earlier by date,
never by counting columns.

Consolidated figures are preferred; companies without subsidiaries only have
standalone figures, so we fall back automatically.
"""
from __future__ import annotations

import calendar
import copy
import re
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from . import http
from .store import Fetched, store

BASE = "https://www.screener.in"
SECTIONS = ("quarters", "profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding")
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}


# ------------------------------------------------------------------ helpers
def to_number(s: Any) -> float | None:
    """'1,23,456' -> 123456.0 ; '27%' -> 27.0 ; '' / '-' -> None."""
    if s is None:
        return None
    t = str(s).replace(",", "").replace("₹", "").replace("%", "").replace("Cr.", "").strip()
    if t in ("", "-", "--", "NA", "N/A"):
        return None
    try:
        return float(t) + 0.0            # + 0.0 turns -0.0 into 0.0
    except ValueError:
        return None


def month_end(label: str) -> str | None:
    """'Sep 2026' -> '2026-09-30'."""
    m = re.match(r"\s*([A-Za-z]{3})[a-z]*\s+(\d{4})", label or "")
    if not m or m.group(1).lower() not in MONTHS:
        return None
    y, mo = int(m.group(2)), MONTHS[m.group(1).lower()]
    return date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()


def _label(td: Tag) -> str:
    """Row label without tooltips, expand buttons or trailing '+'."""
    td = copy.copy(td)
    for tip in td.select(".has-tooltip, .tooltip, i"):
        tip.decompose()
    return re.sub(r"\s*\+\s*$", "", re.sub(r"\s+", " ", td.get_text(" ", strip=True))).strip()


# ------------------------------------------------------------------ fetch
def _fetch_page(key: str) -> tuple[dict, str]:
    last: Exception | None = None
    for view in ("consolidated", "standalone"):
        url = f"{BASE}/company/{key}/consolidated/" if view == "consolidated" else f"{BASE}/company/{key}/"
        try:
            html = http.get_text(url, timeout=40)
        except http.SourceError as e:
            last = e
            continue
        soup = BeautifulSoup(html, "lxml")
        q = soup.select_one("section#quarters table.data-table")
        if q is not None and len(q.select("tbody tr")) > 2:
            return {"html": html, "view": view, "url": url}, f"screener.in ({view})"
        last = LookupError(f"{view} page has no quarterly results")
    raise LookupError(f"screener.in has no data for {key}: {last}")


def company_page(key: str, refresh: bool = False) -> Fetched:
    key = key.strip().upper()
    return store().cached("screener", key, lambda: _fetch_page(key), refresh=refresh)


# ------------------------------------------------------------------ parse
def parse_table(table: Tag) -> dict:
    heads = table.select("thead th")[1:]
    columns = []
    for th in heads:
        label = re.sub(r"\s+", " ", th.get_text(" ", strip=True))
        columns.append({"label": label, "period_end": th.get("data-date-key") or month_end(label)})
    rows: dict[str, list] = {}
    links: dict[str, list] = {}
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        label = _label(tds[0])
        if not label:
            continue
        if label.lower().startswith("raw pdf"):
            links["raw_pdf"] = [td.find("a").get("href") if td.find("a") else None for td in tds[1:]]
            continue
        rows[label] = [to_number(td.get_text(" ", strip=True)) for td in tds[1:]]
    return {"columns": columns, "rows": rows, "links": links}


def _top_ratios(soup: BeautifulSoup) -> dict:
    out = {}
    for li in soup.select("#top-ratios li"):
        name, value = li.select_one(".name"), li.select_one(".value")
        if not name or not value:
            continue
        nums = [to_number(n.get_text()) for n in value.select(".number")]
        nums = [n for n in nums if n is not None]
        out[name.get_text(" ", strip=True)] = {
            "text": re.sub(r"\s+", " ", value.get_text(" ", strip=True)),
            "values": nums,
        }
    return out


def _iso_time(tag: Tag | None) -> str | None:
    t = tag.select_one("time[datetime]") if tag else None
    return t.get("datetime") if t else None


def parse_announcement_list(container: Tag | BeautifulSoup) -> list[dict]:
    items = []
    for li in container.select("li"):
        a = li.find("a")
        if not a or not a.get("href"):
            continue
        ts = _iso_time(li)                      # read before the detail block is removed
        detail_div = a.select_one("div")
        detail = ""
        if detail_div is not None:
            detail = re.sub(r"\s+", " ", detail_div.get_text(" ", strip=True))
            detail = re.sub(r"^\d{1,2} \w{3}(?: \d{4})? - ", "", detail)
            detail_div.extract()
        items.append({
            "title": re.sub(r"\s+", " ", a.get_text(" ", strip=True)),
            "detail": detail,
            "ts": ts,
            "url": a.get("href"),
        })
    return items


def parse_documents(soup: BeautifulSoup) -> dict:
    sec = soup.select_one("section#documents")
    out: dict[str, list] = {"announcements_recent": [], "annual_reports": [], "concalls": [], "credit_ratings": []}
    if sec is None:
        return out
    for blk in sec.select("div.documents"):
        cls = set(blk.get("class") or [])
        if "annual-reports" in cls:
            for a in blk.select("li a"):
                txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
                y = re.search(r"(19|20)\d\d", txt)
                out["annual_reports"].append({
                    "year": int(y.group(0)) if y else None,
                    "title": txt.replace(" AI Summary", ""),
                    "url": a.get("href"),
                })
        elif "concalls" in cls:
            for li in blk.select("li"):
                period_el = li.select_one(".nowrap, .ink-600")
                period = re.sub(r"\s+", " ", period_el.get_text(" ", strip=True)) if period_el else ""
                entry: dict[str, Any] = {"period": period, "month_end": month_end(period),
                                         "transcript": None, "ppt": None, "recording": None}
                for a in li.select("a[href]"):
                    label = (a.get_text(" ", strip=True) + " " + (a.get("title") or "")).lower()
                    href = a.get("href")
                    if "transcript" in label:
                        entry["transcript"] = href
                    elif "ppt" in label or "presentation" in label:
                        entry["ppt"] = href
                    elif label.strip().startswith("rec") or "youtube" in href:
                        entry["recording"] = href
                if entry["transcript"] or entry["ppt"] or entry["recording"]:
                    out["concalls"].append(entry)
        elif "credit-ratings" in cls:
            for a in blk.select("li a"):
                out["credit_ratings"].append({"title": re.sub(r"\s+", " ", a.get_text(" ", strip=True)),
                                              "url": a.get("href")})
        else:
            out["announcements_recent"] = parse_announcement_list(blk)
    return out


def parse_company(html: str, view: str = "", url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")
    tables: dict[str, dict] = {}
    quarter_pdfs: dict[str, str] = {}
    for sid in SECTIONS:
        t = soup.select_one(f"section#{sid} table.data-table")
        if t is None:
            continue
        parsed = parse_table(t)
        raw = parsed.pop("links").get("raw_pdf")
        if raw and sid == "quarters":
            for col, link in zip(parsed["columns"], raw):
                if link and col["period_end"]:
                    # screener links to its own redirect (/company/source/quarter/...),
                    # which forwards to the exchange PDF; documents.py checks the target.
                    quarter_pdfs[col["period_end"]] = BASE + link if link.startswith("/") else link
        tables[sid.replace("-", "_")] = parsed

    bse = re.search(r"bseindia\.com/stock-share-price/[^\"']*?/(\d{6})/", html)
    nse = re.search(r"nseindia\.com/get-quotes/equity\?symbol=([A-Za-z0-9&%\-]+)", html)
    cid = re.search(r'data-company-id="(\d+)"', html)
    about = soup.select_one(".company-profile .about p, .about p")
    h1 = soup.select_one("h1")
    sub = soup.select_one("section#quarters p.sub")
    units = re.sub(r"\s+", " ", sub.get_text(" ", strip=True)) if sub else ""
    return {
        "name": h1.get_text(strip=True) if h1 else None,
        "view": view,
        "url": url,
        "units": "Rs crore" if "Crores" in units else units,
        "company_id": cid.group(1) if cid else None,
        "bse_code": bse.group(1) if bse else None,
        "nse_symbol": nse.group(1).replace("%26", "&") if nse else None,
        "about": re.sub(r"\s+", " ", about.get_text(" ", strip=True)) if about else None,
        "top_ratios": _top_ratios(soup),
        "tables": tables,
        "quarter_pdfs": quarter_pdfs,
        "documents": parse_documents(soup),
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }


def company(key: str, refresh: bool = False) -> Fetched:
    """Fetched(data=parsed company dict)."""
    page = company_page(key, refresh=refresh)
    parsed = parse_company(page.data["html"], page.data["view"], page.data["url"])
    return Fetched(parsed, page.source, page.fetched_at, page.stale, page.error)


def recent_announcements(company_id: str, refresh: bool = False) -> Fetched:
    """The company's recent filings list as screener shows it (newest few, BSE links).
    The raw HTML is cached and parsed on every read, so parser fixes apply at once."""
    def fetch():
        html = http.get_text(f"{BASE}/announcements/recent/{company_id}/",
                             headers={"X-Requested-With": "XMLHttpRequest"})
        return {"html": html}, "screener.in recent"
    f = store().cached("screener_ann", f"{company_id}:html", fetch, refresh=refresh)
    items = parse_announcement_list(BeautifulSoup(f.data["html"], "lxml"))
    return Fetched(items, f.source, f.fetched_at, f.stale, f.error)
