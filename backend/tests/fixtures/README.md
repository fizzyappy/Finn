# Test fixtures

Real responses captured from the live sources on 14 Nov 2026 (IST), so the offline
tests check the parsers against what the sites actually send, not hand-written guesses.

| File | Source |
|---|---|
| `screener_RELIANCE.html`, `screener_HDFCBANK.html` | screener.in company pages (consolidated) |
| `screener_ann_recent_RELIANCE.html` | screener.in recent-announcements fragment |
| `nse_rss.xml` | NSE official RSS: Online_announcements.xml |
| `bse_rss.xml` | BSE official RSS: data/xml/announcements.xml |
| `yahoo_chart_INFY.json` | Yahoo chart API, 5 days (last daily bar still null: a real quirk) |
| `EQUITY_L_sample.csv` | 13 rows of NSE's EQUITY_L.csv company list |
| `transcript_RELIANCE_2pages.pdf` | first 2 pages of RELIANCE's Nov 2026 concall transcript (BSE filing) |
