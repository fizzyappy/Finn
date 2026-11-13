"""Settings in one place: where data lives, how long each kind of data stays fresh,
and how politely we talk to each website."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # the project folder (…/finn)
DATA_DIR = Path(os.environ.get("FINN_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "finn.sqlite"
DOCS_DIR = DATA_DIR / "docs"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# How long a cached answer counts as fresh (seconds). After that we refetch;
# if the refetch fails we serve the old answer and mark it stale.
HOUR = 3600
TTL = {
    "prices": 6 * HOUR,          # end-of-day data changes once a day
    "screener": 24 * HOUR,       # statements change quarterly
    "screener_ann": 15 * 60,     # recent filings list
    "filings_api": 15 * 60,
    "nse_master": 7 * 24 * HOUR,  # list of NSE companies
    "instrument": 30 * 24 * HOUR,
}

# Minimum seconds between two requests to the same host.
MIN_INTERVAL = {
    "www.screener.in": 1.5,
    "www.bseindia.com": 0.5,
    "api.bseindia.com": 1.0,
    "www.nseindia.com": 1.0,
    "nsearchives.nseindia.com": 0.5,
    "query1.finance.yahoo.com": 0.3,
    "query2.finance.yahoo.com": 0.3,
}
DEFAULT_INTERVAL = 0.3

# When a host refuses us (401/403), stop asking it for this long.
BLOCK_COOLDOWN = 30 * 60

MAX_PDF_BYTES = 80 * 1024 * 1024

# Documents are only downloaded from these hosts (exchange filings = primary sources).
DOC_HOSTS = ("bseindia.com", "nseindia.com")
