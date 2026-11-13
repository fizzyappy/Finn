"""Command line:  python -m finn <command> ...

    resolve RELIANCE            search "hdfc bank"
    prices INFY --period 1y     nifty
    results HDFCBANK            fundamentals SUZLON
    docs INFY                   filings RELIANCE --days 7
    poll-rss                    pdf-text <url>
    validate [TICKERS...]       (live check -> backend/validation_report.md)
"""
from __future__ import annotations

import argparse
import json
import sys


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="finn")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("resolve", "results", "fundamentals", "docs"):
        sub.add_parser(name).add_argument("ticker")
    sub.add_parser("search").add_argument("text")
    pr = sub.add_parser("prices")
    pr.add_argument("ticker")
    pr.add_argument("--period", default="1y")
    sub.add_parser("nifty").add_argument("--period", default="1y")
    fl = sub.add_parser("filings")
    fl.add_argument("ticker")
    fl.add_argument("--days", type=int, default=7)
    sub.add_parser("poll-rss")
    sub.add_parser("pdf-text").add_argument("url")
    va = sub.add_parser("validate")
    va.add_argument("tickers", nargs="*")
    a = p.parse_args(argv)

    from . import documents, filings, fundamentals, prices, symbols

    if a.cmd == "resolve":
        _print(symbols.resolve(a.ticker).to_dict())
    elif a.cmd == "search":
        _print(symbols.search(a.text))
    elif a.cmd == "prices":
        f = prices.get_prices(a.ticker, a.period)
        _print({"meta": f.meta(), "summary": prices.summary(f.data), "last_5": f.data[-5:]})
    elif a.cmd == "nifty":
        f = prices.get_index(period=a.period)
        _print({"meta": f.meta(), "summary": prices.summary(f.data)})
    elif a.cmd == "results":
        _print(fundamentals.headline_results(a.ticker))
    elif a.cmd == "fundamentals":
        f = fundamentals.get_fundamentals(a.ticker)
        d = f.data
        _print({"meta": f.meta(), **{k: d[k] for k in ("name", "basis", "units", "lender", "top_ratios")},
                "periods": {k: list(d[k])[-4:] for k in ("quarterly", "annual", "balance_sheet", "cash_flow")}})
    elif a.cmd == "docs":
        d = fundamentals.get_fundamentals(a.ticker).data
        _print({"quarter_pdfs": d["quarter_pdfs"], **d["documents"]})
    elif a.cmd == "filings":
        _print(filings.get_filings(a.ticker, days=a.days))
    elif a.cmd == "poll-rss":
        _print(filings.poll_rss())
    elif a.cmd == "pdf-text":
        t = documents.get_text(a.url)
        _print({k: v for k, v in t.items() if k != "pages"} | {"page_1": t["pages"][0][:1500] if t["pages"] else ""})
    elif a.cmd == "validate":
        from .validate import run

        path = run(a.tickers or None)
        print(f"wrote {path}")
