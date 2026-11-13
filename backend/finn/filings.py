"""Corporate filings (exchange announcements) for any company, from every source
that will talk to us, merged into one de-duplicated list.

Sources, in order:
  1. BSE announcements API      - full history per company. Often refuses scripts (403).
  2. NSE announcements API      - same; needs the homepage visited first, like a browser.
  3. screener.in recent list    - the newest few filings per company, links to BSE PDFs.
  4. RSS store                  - BSE's and NSE's official RSS feeds (market-wide, newest
                                  ~25 items), polled regularly by `poll_rss()` and kept
                                  in SQLite, so coverage grows from the moment polling starts.
A refused source is reported, not hidden: every answer says which sources worked.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from . import http, screener
from .store import store
from .symbols import Instrument, match_company_name, nse_master, resolve

IST = timezone(timedelta(hours=5, minutes=30))

BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
BSE_ATTACH = "https://www.bseindia.com/xml-data/corpfiling/{folder}/{name}"
NSE_API = "https://www.nseindia.com/api/corporate-announcements"
RSS_FEEDS = {
    "BSE": "https://www.bseindia.com/data/xml/announcements.xml",
    "NSE": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
}


# ------------------------------------------------------------------ helpers
def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=IST)
    except ValueError:
        pass
    s = s.split(".")[0]
    for fmt in ("%d-%b-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%d-%b-%Y", "%d/%m/%Y %H:%M:%S", "%a, %d %b %Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None


def doc_key(url: str | None) -> str | None:
    """Same PDF under different BSE URLs -> same key.
    AnnPdfOpen.aspx?Pname=<uuid>.pdf  ==  xml-data/corpfiling/AttachLive/<uuid>.pdf"""
    if not url:
        return None
    u = urlparse(url)
    name = (parse_qs(u.query).get("Pname") or [None])[0] or u.path.rsplit("/", 1)[-1]
    return name.lower() if name else None


def _category_from_title(title: str) -> str:
    """'Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation'
    -> 'Analyst / Investor Meet - Intimation'."""
    m = re.search(r"\(LODR\)\s*-\s*(.+)$", title)
    return (m.group(1) if m else title).strip()


def _item(**kw) -> dict:
    ts = kw.get("ts")
    if isinstance(ts, datetime):
        kw["ts"] = ts.astimezone(IST).isoformat(timespec="seconds")
    kw.setdefault("detail", "")
    kw.setdefault("category", "")
    kw["doc_key"] = doc_key(kw.get("url"))
    return kw


# ------------------------------------------------------------------ 1. BSE API
def _bse_api(code: str, start: datetime, end: datetime, max_pages: int = 10) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, max_pages + 1):
        data = http.get_json(BSE_API, params={
            "pageno": page, "strCat": "-1", "strPrevDate": start.strftime("%Y%m%d"), "strScrip": code,
            "strSearch": "P", "strToDate": end.strftime("%Y%m%d"), "strType": "C", "subcategory": "-1",
        }, headers={"Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"})
        batch = data.get("Table") or []
        rows += batch
        total = ((data.get("Table1") or [{}])[0] or {}).get("ROWCNT") or 0
        if not batch or len(rows) >= total:
            break
    out = []
    for r in rows:
        name = r.get("ATTACHMENTNAME")
        folder = "AttachHis" if str(r.get("PDFFLAG")) == "1" else "AttachLive"
        out.append(_item(
            uid=f"BSE:{r.get('NEWSID')}", exchange="BSE", bse_code=code, company=r.get("SLONGNAME"),
            ts=parse_dt(r.get("DissemDT") or r.get("NEWS_DT")), subject=(r.get("NEWSSUB") or "").strip(),
            detail=re.sub(r"\s+", " ", r.get("HEADLINE") or "").strip(),
            category=" / ".join(x for x in (r.get("CATEGORYNAME"), r.get("SUBCATNAME")) if x),
            url=BSE_ATTACH.format(folder=folder, name=name) if name else r.get("NSURL"),
            source="bse_api",
        ))
    return out


# ------------------------------------------------------------------ 2. NSE API
def _nse_api(symbol: str, start: datetime, end: datetime) -> list[dict]:
    # A browser loads the homepage (which sets cookies) before calling the API.
    http.get("https://www.nseindia.com/", timeout=20)
    data = http.get_json(NSE_API, params={
        "index": "equities", "symbol": symbol,
        "from_date": start.strftime("%d-%m-%Y"), "to_date": end.strftime("%d-%m-%Y"),
    }, headers={"Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements"})
    rows = data if isinstance(data, list) else data.get("data", [])
    return [_item(
        uid=f"NSE:{r.get('seq_id') or r.get('an_dt')}", exchange="NSE", symbol=symbol, company=r.get("sm_name"),
        ts=parse_dt(r.get("sort_date") or r.get("an_dt")), subject=(r.get("desc") or "").strip(),
        detail=(r.get("attchmntText") or "").strip(), category=r.get("desc") or "",
        url=r.get("attchmntFile"), source="nse_api",
    ) for r in rows]


# ------------------------------------------------------------------ 3. screener
def _screener_recent(inst: Instrument) -> list[dict]:
    if not inst.screener_id:
        return []
    items = screener.recent_announcements(inst.screener_id).data
    out = []
    for it in items:
        dk = doc_key(it["url"])
        out.append(_item(
            uid=f"BSE:{dk}" if dk else f"SCR:{it['ts']}:{it['title'][:40]}", exchange="BSE",
            bse_code=inst.bse_code, symbol=inst.symbol, company=inst.name,
            ts=parse_dt(it["ts"]), subject=it["title"], detail=it["detail"],
            category=_category_from_title(it["title"]), url=it["url"], source="screener_recent",
        ))
    return out


# ------------------------------------------------------------------ 4. RSS
def parse_rss(xml_text: str, exchange: str, master: dict | None = None) -> list[dict]:
    root = ET.fromstring(xml_text.lstrip("﻿").strip())
    out = []
    for it in root.iter("item"):
        get = lambda tag: (it.findtext(tag) or "").strip()  # noqa: E731
        title, link, desc = get("title"), get("link"), get("description")
        ts = parse_dt(get("pubDate"))
        if exchange == "BSE":
            code = get("scripcode") or (re.search(r"\((\d{6})\)\s*$", title) or [None, None])[1]
            company = re.sub(r"\s*\(\d{6}\)\s*$", "", title)
            dk = doc_key(link)
            out.append(_item(uid=f"BSE:{dk}" if dk else f"BSE:{code}:{get('pubDate')}", exchange="BSE",
                             bse_code=code, symbol=None, company=company, ts=ts, subject=desc[:300],
                             detail=desc, url=link, source="bse_rss"))
        else:
            subject = desc.split("|SUBJECT:")[-1].strip() if "|SUBJECT:" in desc else desc[:200]
            symbol = None
            m = re.search(r"/corporate/([A-Z0-9&\-]+)_\d{14}_", link)
            if m:
                symbol = m.group(1)
            elif master is not None:
                symbol = match_company_name(title, master)
            dk = doc_key(link)
            out.append(_item(uid=f"NSE:{dk}" if dk else f"NSE:{title}:{get('pubDate')}", exchange="NSE",
                             bse_code=None, symbol=symbol, company=title, ts=ts, subject=subject,
                             detail=desc, category=subject, url=link, source="nse_rss"))
    return out


def poll_rss() -> dict:
    """Fetch both exchanges' RSS feeds once and keep every item. Run every few minutes."""
    status = {}
    try:
        master = nse_master()
    except Exception:  # noqa: BLE001 - NSE items will just lack a symbol
        master = None
    for exch, url in RSS_FEEDS.items():
        try:
            items = parse_rss(http.get_text(url), exch, master)
            new = store().upsert_filings(items)
            status[exch] = f"ok: {len(items)} items, {new} new"
        except Exception as e:  # noqa: BLE001
            status[exch] = f"failed: {type(e).__name__}: {str(e)[:120]}"
    return status


def _rss_store(inst: Instrument, start: datetime) -> list[dict]:
    rows = store().filings_for(bse_code=inst.bse_code, symbol=inst.symbol,
                               since_iso=start.astimezone(IST).isoformat(timespec="seconds"))
    for r in rows:
        r.pop("seen_at", None)
        r["doc_key"] = doc_key(r.get("url"))
    return rows


# ------------------------------------------------------------------ merge
def merge(items: list[dict]) -> list[dict]:
    """One entry per filing. Same PDF -> same filing; otherwise same exchange,
    same minute and same subject -> same filing."""
    merged: dict[str, dict] = {}
    for it in sorted(items, key=lambda x: x.get("ts") or "", reverse=True):
        key = it.get("doc_key") or f"{it.get('exchange')}|{(it.get('ts') or '')[:16]}|{(it.get('subject') or '').lower()[:60]}"
        if key in merged:
            m = merged[key]
            m["sources"] = sorted(set(m["sources"]) | {it["source"]})
            for f in ("detail", "category", "subject"):
                if len(it.get(f) or "") > len(m.get(f) or ""):
                    m[f] = it[f]
            for f in ("symbol", "bse_code", "company"):
                m[f] = m.get(f) or it.get(f)
            continue
        merged[key] = {**it, "sources": [it["source"]]}
    out = list(merged.values())
    for m in out:
        m.pop("source", None)
    return sorted(out, key=lambda x: x.get("ts") or "", reverse=True)


def get_filings(ticker: str, days: int = 7, use_apis: bool = True) -> dict:
    """All filings for one company in the last `days` days, newest first, plus
    a per-source status so the caller always knows how complete the list is."""
    inst = resolve(ticker)
    end = datetime.now(IST)
    start = end - timedelta(days=days)
    status: dict[str, str] = {}
    items: list[dict] = []

    def attempt(name: str, fn):
        try:
            got = fn()
            items.extend(got)
            status[name] = f"ok ({len(got)})"
        except http.SourceBlocked as e:
            status[name] = f"blocked: {e}"
        except Exception as e:  # noqa: BLE001
            status[name] = f"failed: {type(e).__name__}: {str(e)[:120]}"

    if use_apis and inst.bse_code:
        attempt("bse_api", lambda: _bse_api(inst.bse_code, start, end))
    if use_apis and inst.symbol:
        attempt("nse_api", lambda: _nse_api(inst.symbol, start, end))
    attempt("screener_recent", lambda: _screener_recent(inst))
    attempt("rss_store", lambda: _rss_store(inst, start))

    start_iso = start.isoformat(timespec="seconds")
    in_window = [i for i in merge(items) if (i.get("ts") or "") >= start_iso]
    complete = any(status.get(k, "").startswith("ok") for k in ("bse_api", "nse_api"))
    return {
        "instrument": inst.to_dict(),
        "window": {"from": start_iso, "to": end.isoformat(timespec="seconds"), "days": days},
        "status": status,
        "complete": complete,
        "coverage_note": None if complete else (
            "Exchange APIs refused this connection, so this list comes from screener's newest "
            "filings plus the RSS store (which only holds what the poller has seen). It may be incomplete."),
        "items": in_window,
    }
