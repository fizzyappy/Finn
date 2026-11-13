"""finn: FINN's data layer.

Primary sources behind one cached, company-agnostic API:

    symbols       -> any NSE symbol / BSE code / company name -> one Instrument
    prices        -> end-of-day prices (yfinance, Yahoo chart fallback) + Nifty
    fundamentals  -> screener.in statements + headline results (Python arithmetic)
    filings       -> exchange announcements from every source that answers
    documents     -> results PDFs, transcripts, annual reports -> page text
"""
from .documents import find_quote, get_text
from .filings import get_filings, poll_rss
from .fundamentals import get_fundamentals, headline_results
from .prices import get_index, get_prices, summary
from .symbols import Instrument, resolve, search

__all__ = [
    "Instrument", "resolve", "search", "get_prices", "get_index", "summary",
    "get_fundamentals", "headline_results", "get_filings", "poll_rss", "get_text", "find_quote",
]
__version__ = "0.2.0"
