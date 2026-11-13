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

## Push engine (`finn.push`)

What FINN tells the investor without being asked. Portfolio and preferences: `finn/push/portfolio.json`.

| Step | Module |
|---|---|
| Classify into ENAM's 17 categories (rules first, Gemini Flash-Lite for the rest) | `push/taxonomy.py`, `push/classify.py` |
| Materiality score with reasons → hero / one-liner / collapsed | `push/materiality.py` |
| Results card (model reads, Python checks, "verified" badge) | `push/results_card.py` |
| People card (quotes verified word for word) | `push/people.py` |
| One-line summaries (numbers, adjectives and verbs checked) | `push/summarize.py` |
| End-of-day alerts, presets, custom rules, 90-day backtest | `push/alerts.py` |
| Digest → `brief.json` (24h / 3d / 7d / since last look / custom) | `push/digest.py` |
| All LLM calls: tiers, fallback, cache, token log | `finn/llm.py` |

```bash
../.venv/Scripts/python -m finn.push.run          # live run -> push_report.md + out/*.json
```
API: `/brief?window=7d`, `/alerts/backtest?rule=unusual_move`, `/llm/usage`.

## Data on disk

`../data/finn.sqlite` (cache, filings, document index) and `../data/docs/` (PDFs + page
text). Both are git-ignored. Override the location with `FINN_DATA_DIR`.
