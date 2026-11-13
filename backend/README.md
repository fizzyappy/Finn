# FINN backend: data layer (`finn` package)

Prices, filings, fundamentals and primary documents for **any** NSE/BSE-listed
company, behind one cached Python API. No company-specific code.

| Need | Call | Source |
|---|---|---|
| Find a company | `resolve("hdfc bank")`, `search("tata")` | NSE's official company list + screener (BSE code) |
| Daily prices | `get_prices("INFY", "1y")`, `get_index()` (Nifty) | yfinance → Yahoo chart JSON fallback |
| Statements | `get_fundamentals("SUZLON")` | screener.in (consolidated → standalone) |
| Latest results | `headline_results("HDFCBANK")` | computed in Python, YoY matched by period-end date |
| Filings | `get_filings("RELIANCE", days=7)` | BSE API → NSE API → screener recent → RSS store |
| Keep filings flowing | `poll_rss()` (API server runs it every 5 min) | BSE + NSE official RSS feeds |
| Documents | `get_text(url)`, `find_quote(pages, quote)` | exchange PDFs (+ company-site PDFs it lists) |

## Run (from this folder, with the project's virtual environment)

```bash
../.venv/Scripts/python -m pytest                     # offline tests, no network
../.venv/Scripts/python -m finn validate              # live check -> validation_report.md
../.venv/Scripts/python -m finn results INFY
../.venv/Scripts/python -m finn filings RELIANCE --days 7
../.venv/Scripts/python -m uvicorn finn.api:app --reload   # HTTP API, docs at /docs
```

## How it behaves when a source fails

- Every answer says where it came from, when it was fetched, and whether it is stale.
- A site that refuses us (401/403) is left alone for 30 minutes; we never try to get
  around bot protection. Other sources fill in, and the answer says which ones worked.
- If a refresh fails, the last good copy is served and marked `stale`.
- Yahoo often publishes the day's bar late; after 3:30 pm IST the session's last trade
  from Yahoo's own quote is used as a bar marked `provisional`.
- Prices pass data checks (duplicates, gaps, high<low, stale data, >35% one-day jumps).

## Data on disk

`../data/finn.sqlite` (cache, filings, document index) and `../data/docs/` (PDFs + page
text). Both are git-ignored. Override the location with `FINN_DATA_DIR`.
