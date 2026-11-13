"""Cache, fallbacks, block handling, documents: the plumbing that keeps the app up."""
from __future__ import annotations

import time

import pytest

from finn import config, documents, filings, http, store, symbols
from conftest import fixture_bytes


# ------------------------------------------------------------------ cache
def test_cache_fresh_hit_skips_fetch(offline):
    calls = []
    f1 = offline.cached("prices", "k", lambda: (calls.append(1) or [1, 2], "src"))
    f2 = offline.cached("prices", "k", lambda: (calls.append(1) or [9], "src"))
    assert f1.data == f2.data == [1, 2] and len(calls) == 1 and not f2.stale


def test_cache_serves_stale_on_error(offline):
    offline.cached("prices", "k", lambda: ([1], "src"), ttl=0)
    time.sleep(0.01)

    def boom():
        raise http.SourceBlocked("down")

    f = offline.cached("prices", "k", boom, ttl=0)
    assert f.data == [1] and f.stale and "down" in f.error


def test_cache_raises_when_nothing_to_fall_back_on(offline):
    with pytest.raises(ValueError):
        offline.cached("prices", "missing", lambda: (_ for _ in ()).throw(ValueError("x")))


def test_cache_is_json_not_pickle(offline):
    offline.put("x", "k", {"a": 1}, "s")
    raw = offline.conn.execute("SELECT value FROM cache WHERE ns='x'").fetchone()[0]
    assert raw == '{"a": 1}'


# ------------------------------------------------------------------ http blocking
def test_blocked_host_is_not_hit_again(monkeypatch):
    hits = []

    class Resp:
        status_code = 403

    class Sess:
        def get(self, *a, **k):
            hits.append(a[0])
            return Resp()

    monkeypatch.undo()                                   # restore the real http.get
    monkeypatch.setattr(http, "session", lambda host: Sess())
    monkeypatch.setattr(http, "_throttle", lambda host: None)
    http.reset_blocks()
    with pytest.raises(http.SourceBlocked):
        http.get("https://api.bseindia.com/x")
    with pytest.raises(http.SourceBlocked, match="cooling down"):
        http.get("https://api.bseindia.com/y")
    assert hits == ["https://api.bseindia.com/x"]
    http.reset_blocks()


# ------------------------------------------------------------------ filings orchestration
def test_get_filings_reports_each_source(monkeypatch, offline):
    offline.put("instrument", "RELIANCE", {"symbol": "RELIANCE", "bse_code": "500325", "name": "Reliance Industries Limited",
                                           "isin": "INE002A01018", "series": "EQ", "screener_id": "2726"}, "fixture")

    def blocked(*a, **k):
        raise http.SourceBlocked("api.bseindia.com returned 403")

    now = filings.datetime.now(filings.IST).isoformat(timespec="seconds")
    monkeypatch.setattr(filings, "_bse_api", blocked)
    monkeypatch.setattr(filings, "_nse_api", blocked)
    monkeypatch.setattr(filings, "_screener_recent", lambda inst: [filings._item(
        uid="BSE:a.pdf", exchange="BSE", ts=now, subject="Results", url="https://www.bseindia.com/x/a.pdf",
        source="screener_recent")])
    offline.upsert_filings([filings._item(uid="BSE:a.pdf", exchange="BSE", bse_code="500325", ts=now,
                                          subject="Results with more words", url="https://www.bseindia.com/y/a.pdf",
                                          source="bse_rss")])
    r = filings.get_filings("RELIANCE", days=7)
    assert r["status"]["bse_api"].startswith("blocked") and r["status"]["screener_recent"] == "ok (1)"
    assert r["status"]["rss_store"] == "ok (1)"
    assert len(r["items"]) == 1 and r["items"][0]["sources"] == ["bse_rss", "screener_recent"]
    assert r["complete"] is False and r["coverage_note"]


def test_resolve_unknown_suggests(monkeypatch):
    with pytest.raises(LookupError, match="Did you mean"):
        symbols._resolve("RELIANCEX")


# ------------------------------------------------------------------ documents
def test_pdf_text_extraction_and_quote_check():
    pages, method = documents.extract_pages(fixture_bytes("transcript_RELIANCE_2pages.pdf"))
    assert len(pages) == 2 and method in ("pypdf", "pdfplumber")
    text = " ".join(pages)
    assert len(text) > 200
    line = next(l for p in pages for l in p.splitlines() if len(l.split()) >= 6)
    assert documents.find_quote(pages, line) is not None
    assert documents.find_quote(pages, line.upper() + " invented words") is None


def test_documents_only_from_exchanges():
    assert documents.allowed("https://www.bseindia.com/xml-data/corpfiling/AttachHis/x.pdf")
    assert documents.allowed("https://nsearchives.nseindia.com/corporate/x.pdf")
    assert not documents.allowed("https://evil.example.com/x.pdf")
    assert not documents.allowed("http://www.bseindia.com/x.pdf")
    assert not documents.allowed("https://bseindia.com.evil.io/x.pdf")
    with pytest.raises(ValueError, match="only fetched"):
        documents._download("https://example.com/report.pdf")


def test_company_site_pdf_only_when_listed(monkeypatch):
    data = fixture_bytes("transcript_RELIANCE_2pages.pdf")
    url = "https://investors.example-co.com/q2-transcript.pdf"

    class R:
        def __init__(self, final):
            self.url = final
        headers = {"content-type": "application/pdf"}

        def iter_content(self, n):
            yield data

    monkeypatch.setattr(http, "get", lambda u, **k: R(u))
    with pytest.raises(ValueError, match="only fetched"):
        documents._download(url)                                   # not listed -> refused
    assert documents._download(url, frozenset({url}))[0] == data   # listed by the company -> ok
    monkeypatch.setattr(http, "get", lambda u, **k: R("https://elsewhere.example.net/x.pdf"))
    with pytest.raises(ValueError, match="did not lead"):
        documents._download(url, frozenset({url}))                 # redirect off-site -> refused


def test_recent_announcements_cache_raw_html(offline):
    from finn import screener
    from conftest import fixture_text

    offline.put("screener_ann", "2726:html", {"html": fixture_text("screener_ann_recent_RELIANCE.html")}, "fixture")
    items = screener.recent_announcements("2726").data
    assert len(items) == 5 and all(i["ts"] for i in items)


def test_cover_letter_transcript_is_skipped(monkeypatch):
    from finn import fundamentals

    cands = [{"date": "2026-11-10", "url": "https://www.bseindia.com/new.pdf", "title": "T", "via": "filings"},
             {"date": "2026-06-30", "url": "https://www.bseindia.com/old.pdf", "title": "T", "via": "concall list"}]
    texts = {"https://www.bseindia.com/new.pdf": ["Transcript is at https://investors.example.com/results/"],
             "https://www.bseindia.com/old.pdf": ["page"] * 12}
    monkeypatch.setattr(fundamentals, "transcript_candidates", lambda t: cands)
    monkeypatch.setattr(fundamentals, "document_links", lambda t: set())
    monkeypatch.setattr(documents, "get_text", lambda url, **k: {
        "page_count": len(texts[url]), "text_chars": 99, "pages": texts[url]})
    r = fundamentals.latest_transcript("X")
    assert r["url"].endswith("old.pdf") and r["pages"] == 12
    assert r["skipped"][0]["reason"].startswith("cover letter")
    assert r["skipped"][0]["points_to"] == ["https://investors.example.com/results/"]


def test_negative_zero_is_zero():
    from finn import screener

    v = screener.to_number("-0")
    assert v == 0 and str(v) == "0.0"


def test_fetch_pdf_rejects_non_pdf(monkeypatch):
    class R:
        url = "https://www.bseindia.com/a.pdf"
        headers = {"content-type": "text/html"}

        def iter_content(self, n):
            yield b"<html>login</html>"

    monkeypatch.setattr(http, "get", lambda *a, **k: R())
    with pytest.raises(documents.NotAPdf):
        documents.fetch_pdf("https://www.bseindia.com/a.pdf")


def test_fetch_pdf_stores_by_hash(monkeypatch, offline):
    data = fixture_bytes("transcript_RELIANCE_2pages.pdf")

    class R:
        url = "https://www.bseindia.com/a.pdf"
        headers = {"content-type": "application/pdf"}

        def iter_content(self, n):
            yield data

    monkeypatch.setattr(http, "get", lambda *a, **k: R())
    rec = documents.fetch_pdf("https://www.bseindia.com/a.pdf")
    assert rec["bytes"] == len(data) and rec["path"].endswith(rec["sha256"] + ".pdf")
    t = documents.get_text("https://www.bseindia.com/a.pdf")
    assert t["page_count"] == 2 and t["status"] == "ok"
    assert offline.get_document("https://www.bseindia.com/a.pdf")["pages"] == 2
