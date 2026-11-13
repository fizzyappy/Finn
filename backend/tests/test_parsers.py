"""Parsers against real responses captured from the live sources (see fixtures/README.md)."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from finn import filings, fundamentals, prices, screener, symbols
from conftest import fixture_text


# ------------------------------------------------------------------ symbols
def test_normalise_variants():
    assert symbols.normalise("reliance.ns") == "RELIANCE"
    assert symbols.normalise("NSE:M&M") == "M&M"
    assert symbols.normalise("500325.BO") == "500325"
    assert symbols.normalise(" bse: 500325 ") == "500325"


def test_master_parsing_and_search():
    m = symbols.nse_master()
    assert m["RELIANCE"]["isin"] == "INE002A01018"
    assert symbols.search("hdfc bank")[0]["symbol"] == "HDFCBANK"
    assert symbols.search("INFY")[0]["symbol"] == "INFY"
    assert symbols.search("reliance industries")[0]["symbol"] == "RELIANCE"


def test_company_name_match():
    assert symbols.match_company_name("Reliance Industries Ltd") == "RELIANCE"
    assert symbols.match_company_name("No Such Company Limited") is None


# ------------------------------------------------------------------ screener
def test_screener_company_tables_and_dates():
    d = screener.parse_company(fixture_text("screener_RELIANCE.html"), "consolidated")
    assert d["bse_code"] == "500325"
    assert d["nse_symbol"] == "RELIANCE"
    assert d["company_id"] == "2726"
    assert d["units"] == "Rs crore"
    q = d["tables"]["quarters"]
    assert q["columns"][-1] == {"label": "Sep 2026", "period_end": "2026-09-30"}
    assert q["rows"]["Sales"][-1] == 330601.0
    assert q["rows"]["OPM %"][-1] == 17.0
    assert "Raw PDF" not in q["rows"]
    # tooltip text must not leak into row labels
    assert "CFO/EBITDA" in d["tables"]["cash_flow"]["rows"]
    assert set(d["tables"]) >= {"quarters", "profit_loss", "balance_sheet", "cash_flow", "ratios", "shareholding"}
    # shareholding headers have no data-date-key; derived from the label
    assert all(c["period_end"] for c in d["tables"]["shareholding"]["columns"])


def test_screener_documents():
    docs = screener.parse_company(fixture_text("screener_RELIANCE.html"))["documents"]
    ar = docs["annual_reports"]
    assert ar[0]["year"] == 2026 and "bseindia.com" in ar[0]["url"]
    assert "AI Summary" not in ar[0]["title"]
    calls = docs["concalls"]
    assert calls[0]["period"] == "Nov 2026" and calls[0]["month_end"] == "2026-11-30"
    assert "bseindia.com" in calls[0]["transcript"]
    assert calls[0]["recording"] and "youtube" in calls[0]["recording"]
    assert len(docs["announcements_recent"]) == 5


def test_screener_recent_announcements_keep_dates():
    items = screener.parse_announcement_list(BeautifulSoup(fixture_text("screener_ann_recent_RELIANCE.html"), "lxml"))
    assert len(items) == 5
    assert all(i["ts"] and i["ts"].startswith("2026-11") for i in items)
    assert all(not i["title"].endswith(i["detail"]) or not i["detail"] for i in items)


def test_to_number():
    assert screener.to_number("1,23,456") == 123456.0
    assert screener.to_number("-12.5%") == -12.5
    assert screener.to_number("") is None and screener.to_number("-") is None
    assert screener.month_end("Feb 2024") == "2024-02-29"


# ------------------------------------------------------------------ fundamentals
def test_lender_detection_from_labels():
    rel = screener.parse_company(fixture_text("screener_RELIANCE.html"))
    bank = screener.parse_company(fixture_text("screener_HDFCBANK.html"))
    assert not fundamentals.is_lender(rel["tables"])
    assert fundamentals.is_lender(bank["tables"])
    q = fundamentals.canonical(bank["tables"]["quarters"])
    latest = q[max(q)]
    assert "financing_profit" in latest and "ebitda" not in latest
    assert "deposits" in fundamentals.canonical(bank["tables"]["balance_sheet"])[max(fundamentals.canonical(bank["tables"]["balance_sheet"]))]


def test_growth_rules():
    assert fundamentals.growth_pct(110, 100) == (10.0, None)
    assert fundamentals.growth_pct(50, -100) == (None, "turned positive (from a loss)")
    assert fundamentals.growth_pct(-50, -100) == (None, "loss in both periods")
    assert fundamentals.growth_pct(-10, 100) == (-110.0, "turned negative")
    assert fundamentals.growth_pct(5, 0) == (None, "base is zero")
    assert fundamentals.growth_pct(None, 1) == (None, "missing")


def test_year_ago_matches_by_date():
    assert fundamentals._year_ago("2026-09-30") == "2025-09-30"
    assert fundamentals._year_ago("2024-02-29") == "2023-02-28"
    assert fundamentals._year_ago("2026-03-31") == "2025-03-31"


def test_headline_results_offline(monkeypatch, offline):
    html = fixture_text("screener_RELIANCE.html")
    offline.put("screener", "RELIANCE", {"html": html, "view": "consolidated", "url": "u"}, "fixture")
    offline.put("instrument", "RELIANCE", {"symbol": "RELIANCE", "bse_code": "500325", "name": "Reliance Industries Limited",
                                           "isin": "INE002A01018", "series": "EQ", "screener_id": "2726"}, "fixture")
    r = fundamentals.headline_results("RELIANCE")
    assert r["quarter_end"] == "2026-09-30" and r["year_ago_quarter_end"] == "2025-09-30"
    rev = r["metrics"]["revenue"]
    assert rev["value"] == 330601.0
    assert rev["yoy_pct"] == round((rev["value"] / rev["year_ago"] - 1) * 100, 1)
    assert r["metrics"]["ebitda_margin_pct"]["value"] == round(r["metrics"]["ebitda"]["value"] / rev["value"] * 100, 1)


# ------------------------------------------------------------------ prices
def test_yahoo_chart_parse_and_clean():
    bars = prices.parse_chart_json(json.loads(fixture_text("yahoo_chart_INFY.json")))
    assert bars[-1]["date"] == "2026-11-13" and bars[-1]["close"] is None   # Yahoo's late daily bar
    cleaned = prices.clean(bars)
    assert cleaned[-1]["date"] == "2026-11-12" and cleaned[-1]["close"] == 1151.2


def test_provisional_bar_only_after_close():
    from datetime import datetime

    meta = json.loads(fixture_text("yahoo_chart_INFY.json"))["chart"]["result"][0]["meta"]
    after = datetime(2026, 11, 13, 16, 0, tzinfo=prices.IST)
    during = datetime(2026, 11, 13, 11, 0, tzinfo=prices.IST)
    pb = prices.provisional_bar(meta, now=after)
    assert pb["date"] == "2026-11-13" and pb["close"] == 1141.5 and pb["provisional"]
    assert prices.provisional_bar(meta, now=during) is None


def test_quality_checks_flag_problems():
    from datetime import date

    good = [{"date": f"2026-01-{d:02d}", "open": 10, "high": 11, "low": 9, "close": 10, "adj_close": 10, "volume": 5}
            for d in range(1, 11)]
    assert prices.check_bars(good, today=date(2026, 1, 11)) == []
    bad = good + [{"date": "2026-03-01", "open": 10, "high": 9, "low": 11, "close": 20, "adj_close": 20, "volume": 0}]
    issues = " | ".join(prices.check_bars(bad, today=date(2026, 3, 30)))
    for word in ("high below low", "gap", "days old", "35%"):
        assert word in issues, issues


def test_summary_arithmetic():
    bars = [{"date": "d1", "open": 1, "high": 105, "low": 95, "close": 100, "adj_close": 100, "volume": 1},
            {"date": "d2", "open": 1, "high": 112, "low": 99, "close": 110, "adj_close": 110, "volume": 2}]
    s = prices.summary(bars)
    assert s["change_pct"] == 10.0 and s["high_52w"] == 112 and s["low_52w"] == 95


# ------------------------------------------------------------------ filings
def test_rss_parsing_both_exchanges():
    bse = filings.parse_rss(fixture_text("bse_rss.xml"), "BSE")
    assert len(bse) == 28
    assert bse[0]["bse_code"] == "544995" and bse[0]["company"] == "Fusion CX Ltd"
    assert bse[0]["ts"].startswith("2026-11-14T00:51") and bse[0]["ts"].endswith("+05:30")
    nse = filings.parse_rss(fixture_text("nse_rss.xml"), "NSE", symbols.nse_master())
    assert len(nse) == 22
    assert nse[0]["symbol"] == "ORIANA"                      # from the PDF file name
    assert nse[0]["subject"].startswith("Outcome of Boar")


def test_doc_key_matches_same_pdf_across_urls():
    a = "https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=3f614a9e-94b0-42ef-8145-ba0055ba7be5.pdf"
    b = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/3f614a9e-94b0-42ef-8145-ba0055ba7be5.pdf"
    assert filings.doc_key(a) == filings.doc_key(b)


def test_merge_dedupes_and_keeps_richest_text():
    url1 = "https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=x1.pdf"
    url2 = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/x1.pdf"
    items = [
        filings._item(uid="a", exchange="BSE", ts="2026-11-13T18:23:17+05:30", subject="Short", url=url1, source="screener_recent"),
        filings._item(uid="b", exchange="BSE", ts="2026-11-13T18:23:17+05:30", subject="A longer subject", url=url2,
                      detail="details", source="bse_rss"),
        filings._item(uid="c", exchange="BSE", ts="2026-11-12T10:00:00+05:30", subject="Other", url=None, source="bse_rss"),
    ]
    out = filings.merge(items)
    assert len(out) == 2
    assert out[0]["sources"] == ["bse_rss", "screener_recent"]
    assert out[0]["subject"] == "A longer subject" and out[0]["detail"] == "details"


def test_category_from_title():
    t = "Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation"
    assert filings._category_from_title(t) == "Analyst / Investor Meet - Intimation"
