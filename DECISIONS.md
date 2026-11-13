# Decisions

| Decision | Why | What we gave up |
|----------|-----|-----------------|
| Project lives in `C:\Users\aparn\Documents\finn` (local, not OneDrive) | OneDrive sync fights with `node_modules`, `.venv` and SQLite files | Automatic cloud backup; GitHub is the backup instead |
| Earlier code kept in `_old\` (git-ignored), rewritten in `backend/finn` | Old code was well designed but never ran against live sources (its own notes say so) and was written for a different LLM provider | Some old features (classifier, push digest, research engine) not ported yet; they come back in Tasks 3–4 |
| Cache stores JSON in SQLite, never pickle | Readable, safe to load, survives pandas upgrades | Slightly more code to turn data into tables |
| Cache raw pages, parse on every read | A parser fix applies at once instead of after the cache expires (we hit this bug live) | A few ms of parsing per read |
| Never work around bot protection. A 401/403 marks the host blocked for 30 min | Respect the sites' wishes; the safety check on this PC also refused browser-fingerprint tricks | BSE and NSE announcement APIs are unusable from this PC (both return 403) |
| Filings come from 4 sources merged: BSE API, NSE API, screener recent list, RSS store | No single free source is complete. Each answer reports which sources worked | Full 7-day history is not guaranteed until the RSS poller has run for a while |
| Poll BSE + NSE official RSS every 5 minutes into SQLite | RSS feeds are published for programs to read, and they work from this PC | The feeds hold only the newest ~25 items, so very busy periods can be missed between polls |
| Company list from NSE's own `EQUITY_L.csv`; BSE code from screener | Primary source, covers every NSE company, gives ISIN | BSE-only companies resolve only by their 6-digit code |
| Match a quarter to the year-ago quarter by period-end date | Counting columns breaks when a column is missing | None |
| Growth % is withheld (with a reason) when the base is zero or negative | "+250% profit" from a loss misleads investors | Some cells show a note instead of a number |
| Banks/NBFCs detected from row labels (Financing Profit, NPA), not a list of names | Works for every lender, no company-specific code | None |
| Prices: yfinance first, Yahoo chart JSON as fallback; late daily bar filled from Yahoo's quote and marked provisional | yfinance is what the challenge suggests; the fallback survives yfinance breakages; we saw the late-bar quirk live | Provisional bars have no opening price |
| Results document = the results filing if found, else the investor presentation filed after the quarter ended | screener's own results PDFs require a screener login; we do not create accounts | Some companies (e.g. INFY this quarter) have no reachable results PDF from this PC |
| PDFs only from exchange sites, or company-site PDFs that the company's own document list links to | Primary sources only; stops the API being used to fetch arbitrary URLs | PDFs elsewhere on the web are refused |
| Keep extracted PDF text exactly as extracted; normalise only for searching | Quotes must match the source word for word | Raw text has PDF line breaks |
| Gemini models: `gemini-3.5-flash-lite` (fast, bulk), `gemini-3.5-flash` (harder tasks), behind one router (Task 3) | Tested live with this key: both answer. `gemini-2.5-*` is closed to new keys; `gemini-3.8-flash` timed out | Newest models not used until they respond reliably |
