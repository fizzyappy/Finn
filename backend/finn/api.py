"""HTTP API for the app.  Run from backend/:  uvicorn finn.api:app --reload

Every answer carries where it came from and how fresh it is, and a refused or
failing source degrades the answer instead of breaking it.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import documents, filings, fundamentals, http, prices, symbols

RSS_POLL_SECONDS = 300
log = logging.getLogger("finn")


async def _poll_forever():
    """Keep the filings store growing while the server runs (official RSS feeds)."""
    while True:
        try:
            status = await asyncio.to_thread(filings.poll_rss)
            log.info("rss poll: %s", status)
        except Exception as e:  # noqa: BLE001
            log.warning("rss poll failed: %s", e)
        await asyncio.sleep(RSS_POLL_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(_app):
    # A fresh server (e.g. Render after a restart) starts from the committed seed:
    # model answers and finished research are reused, not paid for again.
    try:
        from . import seed

        log.info("seed: %s", await asyncio.to_thread(seed.load))
    except Exception as e:  # noqa: BLE001
        log.warning("seed load failed: %s", e)
    task = asyncio.create_task(_poll_forever())
    yield
    task.cancel()


app = FastAPI(title="FINN data API", version="0.3.0", lifespan=lifespan)
# Read-only public data, no cookies: any origin (the Vercel app, localhost) may call it.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/")
def root():
    return {"name": "FINN research engine", "docs": "/docs", "health": "/health", "sources": "/sources"}


@app.get("/sources")
def r_sources():
    """Can this server reach each data source? (Cloud hosts are sometimes refused.)"""
    checks = {
        "yahoo_prices": "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=5d&interval=1d",
        "screener": "https://www.screener.in/company/INFY/",
        "bse_rss": filings.RSS_FEEDS["BSE"],
        "nse_rss": filings.RSS_FEEDS["NSE"],
        "nse_company_list": symbols.NSE_MASTER_URL,
    }
    out = {}
    for name, url in checks.items():
        try:
            r = http.get(url, timeout=15)
            out[name] = {"ok": True, "status": r.status_code}
        except http.SourceBlocked as e:
            out[name] = {"ok": False, "why": f"refused this server ({e})"}
        except Exception as e:  # noqa: BLE001
            out[name] = {"ok": False, "why": f"{type(e).__name__}: {str(e)[:100]}"}
    from . import llm

    out["gemini_key_configured"] = llm.router().available
    return out


def _guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except http.SourceBlocked as e:
        raise HTTPException(503, f"source refused: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"upstream: {type(e).__name__}: {e}") from e


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/search")
def r_search(q: str):
    return _guard(symbols.search, q)


@app.get("/resolve/{ticker}")
def r_resolve(ticker: str):
    return _guard(symbols.resolve, ticker).to_dict()


@app.get("/prices/{ticker}")
def r_prices(ticker: str, period: str = "1y"):
    f = _guard(prices.get_prices, ticker, period)
    return {"meta": f.meta(), "summary": prices.summary(f.data), "bars": f.data}


@app.get("/index/nifty")
def r_nifty(period: str = "1y"):
    f = _guard(prices.get_index, prices.NIFTY, period)
    return {"meta": f.meta(), "summary": prices.summary(f.data), "bars": f.data}


@app.get("/fundamentals/{ticker}")
def r_fundamentals(ticker: str):
    f = _guard(fundamentals.get_fundamentals, ticker)
    return {"meta": f.meta(), **f.data}


@app.get("/results/{ticker}")
def r_results(ticker: str):
    return _guard(fundamentals.headline_results, ticker)


@app.get("/results-document/{ticker}")
def r_results_doc(ticker: str):
    return _guard(fundamentals.results_document, ticker)


@app.get("/filings/{ticker}")
def r_filings(ticker: str, days: int = 7):
    return _guard(filings.get_filings, ticker, days)


@app.post("/rss/poll")
def r_poll():
    return filings.poll_rss()


@app.get("/brief")
def r_brief(window: str = "24h", start: str | None = None, end: str | None = None, mark_seen: bool = False):
    """The push digest. window = 24h | 3d | 7d | since_last_look, or pass start & end (ISO)."""
    from .push import digest

    w = (start, end) if start and end else window
    return _guard(digest.build, w, mark_seen=mark_seen)


@app.get("/alerts/backtest")
def r_backtest(rule: str = "unusual_move", days: int = 90):
    from .push import alerts, portfolio

    series, _ = alerts.portfolio_series(portfolio.load().symbols)
    return _guard(alerts.backtest, rule, series, days)


@app.get("/alerts")
def r_alerts(window: str = "7d", rule: str | None = None):
    """Price/volume alerts fired in the window (default rule from the portfolio)."""
    from .push import alerts, digest, portfolio

    p = portfolio.load()
    start, end, _ = digest.resolve_window(window, digest.datetime.now(digest.IST))
    series, status = alerts.portfolio_series(p.symbols)
    rules = [alerts.rule_from(rule)] if rule else [alerts.rule_from(r) for r in p.alert_rules]
    dates = {r["date"] for rows in series.values() for r in rows
             if start.date().isoformat() <= r["date"] <= end.date().isoformat()}
    return {"window": window, "rules": [r.__dict__ for r in rules], "alerts": alerts.fired(series, rules, dates)}


@app.post("/research/{ticker}")
def r_research_start(ticker: str, refresh: bool = False):
    """Start (or join) a research job. Poll /research/jobs/{id}; table sections appear first."""
    from .pull import engine

    return engine.status(engine.start(ticker, refresh)["id"])


@app.get("/research/jobs/{job_id}")
def r_research_status(job_id: str):
    from .pull import engine

    st = engine.status(job_id)
    if not st:
        raise HTTPException(404, "unknown job")
    return st


@app.get("/research/jobs/{job_id}/result")
def r_research_result(job_id: str):
    from .pull import engine

    res = engine.result(job_id)
    if not res:
        raise HTTPException(404, "not finished yet (check /research/jobs/{id})")
    return res


@app.post("/ask/{ticker}")
def r_ask(ticker: str, body: dict):
    """Q&A about one researched company, answered only from its verified evidence."""
    from .pull import ask, engine

    research = engine.cached_research(ticker)
    if not research:
        raise HTTPException(404, f"{ticker.upper()} has not been researched yet: open it in Research first")
    return ask.ask(research, str(body.get("question", "")))


@app.get("/research/{ticker}/vs-guidance")
def r_vs_guidance(ticker: str, quarter_end: str):
    from .pull import engine

    return {"ticker": ticker.upper(), "quarter_end": quarter_end, "targets": engine.vs_guidance(ticker, quarter_end)}


@app.get("/llm/usage")
def r_llm_usage(since: float = 0.0):
    from . import llm

    return llm.usage(since)


@app.get("/document")
def r_document(url: str, ticker: str | None = None):
    """Exchange-hosted PDFs always; a company-site PDF only if it is listed in
    that company's own documents (pass ?ticker=)."""
    trusted = _guard(fundamentals.document_links, ticker) if ticker else set()
    t = _guard(documents.get_text, url, trusted=trusted)
    return {k: v for k, v in t.items() if k != "path"}
