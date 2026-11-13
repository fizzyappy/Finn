# FINN push engine: live run

Run 2026-11-14 04:26 IST on this PC, demo portfolio of 18 holdings. Everything below was produced live; the full output is in `backend/out/brief_7d.json` and `brief_custom.json` (14 days).

RSS poll: {'BSE': 'ok: 28 items, 0 new', 'NSE': 'ok: 22 items, 0 new'}

## 1. Classifier accuracy (hand-labelled real filings)

| Set | Filings | Category correct | Treatment correct (hero / one-liner / collapsed) |
|---|---|---|---|
| Portfolio filings, rules + Gemini | 90 | 100% | 98% |
| Other companies (RSS), rules only | 34 | 82% | – |
| Other companies (RSS), rules + Gemini | 34 | 100% | – |

Honest caveat: the rules were written after seeing the portfolio set, and fixed after a first pass on the other-company set (first pass: rules alone 53%, rules + Gemini 82%). Both numbers above are therefore in-sample. Treatment confusion: collapsed -> collapsed: 59, one_liner -> one_liner: 20, one_liner -> collapsed: 2, hero -> hero: 9

Remaining disagreements with my labels:
- HDFCBANK: “Shareholder Meeting / Postal Ballot-Outcome of Postal_Ballot” labelled postal_ballot/one_liner, engine says postal_ballot/collapsed (score 0.193)
- HDFCBANK: “Announcement under Regulation 30 (LODR)-Change in Management” labelled management_change/one_liner, engine says management_change/collapsed (score 0.297)

## 2. Digest: last 7 days

**22 filings, 4 matter · 2 price/volume alerts** · window 2026-11-07T04:26 → 2026-11-14T04:26

### Hero cards
- **BAJFINANCE** · fund raise / equity · score 0.834 · 2026-11-11 17:06
  - Headline: Bajaj Finance Approved QIP Opening at Floor Price of ₹992.25  
  - One line: On November 11, 2026, Bajaj Finance authorized opening a qualified institutions placement at a floor price of ₹992.25 per equity share. _(by llm (gemini-3.5-flash-lite))_
  - Why: fund raise / equity (0.72); holding weight 6.0% (1.02); stock moved unusually on 2026-11-12: +3.4% (+2.2 sigma vs its normal), volume 1.2x (0.1)

### One-liners
- **HDFCBANK** (0.495): On November 12, 2026, the RBI approved the re-appointment of V. Srinivasa Rangan as Executive Director for 1 year from November 23, 2026.
- **LT** (0.468): On November 9, 2026, L&T secured an order from Noida Metro Rail Corporation Ltd for the Aqua Line Extension Project.
- **BAJFINANCE** (0.408): Bajaj Finance submitted the half yearly report on 7 November 2026, reporting a consolidated profit after tax of ₹ 12,447 crore for H1 FY27.

### Collapsed
investor meetings 10, press release 2, earnings call 2, unclassified 1

### Price / volume alerts
- 2026-11-12: CDSL +3.4% (Nifty +0.2%) - 2.0 sigma above its normal day after the market move (usual swing 1.6%); volume 3.3x its 20-day average (Volume at least 2.5x its 20-day average)
- 2026-11-11: CDSL +3.8% (Nifty +0.8%) - 1.8 sigma above its normal day after the market move (usual swing 1.6%); volume 3.3x its 20-day average (Volume at least 2.5x its 20-day average)

Gemini use for this brief: gemini-3.5-flash-lite: 0 calls, 5 cache hits, 0 tokens · cost free tier (USD 0)
Built in 7.9 s. Sources refused on this connection: bse_api, nse_api. Filings come from screener's recent list and the BSE/NSE RSS store, so older or very busy days may be incomplete.

## 3. Digest: last 14 days (to show results season)

**73 filings, 16 matter · 13 price/volume alerts** · window 2026-10-31T04:26 → 2026-11-14T04:26

### Hero cards
- **BAJFINANCE** · fund raise / equity · score 0.834 · 2026-11-11 17:06
  - Headline: Bajaj Finance Approved QIP Opening at Floor Price of ₹992.25  
  - One line: On November 11, 2026, Bajaj Finance authorized opening a qualified institutions placement at a floor price of ₹992.25 per equity share. _(by llm (gemini-3.5-flash-lite))_
  - Why: fund raise / equity (0.72); holding weight 6.0% (1.02); stock moved unusually on 2026-11-12: +3.4% (+2.2 sigma vs its normal), volume 1.2x (0.1)
- **ITC** · results / financials · score 0.765 · 2026-11-02 18:24
  - Headline: ITC results: PAT Rs 4,229 cr, -18.5% YoY  
  - One line: Quarter to 30 Sep 2026, consolidated: revenue Rs 20,269 cr (+3.9% YoY), EBITDA Rs 5,742 cr (-15.1% YoY), PAT Rs 4,229 cr (-18.5% YoY) _(by from verified results card)_
  - Results card: **verified** (quarter, consolidated; pages [9]; model gemini-3.5-flash-lite)
    - Checks: 8/8 passed
  - Why: results / financials (0.75); holding weight 6.0% (1.02)
- **HAPPSTMNDS** · results / financials · score 0.728 · 2026-11-04 19:03
  - Headline: HAPPSTMNDS results: PAT Rs 62 cr, +15.1% YoY  
  - One line: Quarter to 30 Sep 2026, consolidated: revenue Rs 645 cr (+12.5% YoY), EBITDA Rs 121 cr (+23.1% YoY), PAT Rs 62 cr (+15.1% YoY) _(by from verified results card)_
  - Results card: **verified** (quarter, consolidated; pages all (no text layer to locate the table); model gemini-3.5-flash-lite)
    - Checks: 8/8 passed
  - Why: results / financials (0.75); holding weight 3.5% (0.97)
- **MAPMYINDIA** · results / press release · score 0.701 · 2026-11-04 15:17
  - Headline: C.E. Info Systems Announces Q2FY2027 Results  
  - One line: On November 4, 2026, C.E. Info Systems reported Q2FY27 revenue of Rs 131.7 Cr, EBITDA of Rs 45 Cr, and PAT of Rs 35.3 Cr. _(by llm (gemini-3.5-flash-lite))_
  - Why: results / press release (0.62); holding weight 3.5% (0.97); stock moved unusually on 2026-11-04: +5.4% (+2.1 sigma vs its normal), volume 11.5x (0.1)

### One-liners
- **SUNPHARMA** (0.513): Clarification was sought from Sun Pharmaceutical Industries Ltd.
- **HDFCBANK** (0.495): On November 12, 2026, the RBI approved the re-appointment of V. Srinivasa Rangan as Executive Director for 1 year from November 23, 2026.
- **LT** (0.468): On November 2, 2026, L&T secured multiple orders from a client for residential and commercial developments in Mumbai, Bengaluru, and…
- **ITC** (0.428): On 2nd November, 2026, ITC approved the amalgamation of Sproutlife Foods Private Limited, with effect from 1st April, 2026.
- **BAJFINANCE** (0.408): Bajaj Finance submitted the half yearly report on 7 November 2026, reporting a consolidated profit after tax of ₹ 12,447 crore for H1 FY27.
- **VEDL** (0.397): Clarification was sought from Vedanta Ltd.
- **SUZLON** (0.397): On 4th November 2026, Suzlon Energy informed the exchanges that it noticed a Material Price Movement on BSE Limited without mainstream…
- **MARUTI** (0.367): Maruti Suzuki sold 276,120 units in October 2026, with domestic sales of 216,789 units and 49,872 exports.
- **PERSISTENT** (0.36): On November 4, 2026, Persistent Systems approved the allotment of 700,000 non-convertible debentures aggregating to INR 70 billion.
- **IEX** (0.346): Indian Energy Exchange reported 13.1 BU of electricity traded volume in October 2026, marking a 16.5% year-on-year increase.
- **RELIANCE** (0.32): On October 30, 2026, Reliance Industries released the earnings transcript for the quarter ended September 30, 2026.
- **SUNPHARMA** (0.304): Sun Pharmaceutical Industries Limited reported Q2 FY27 sales of INR 1,61,000 million on November 4, 2026.

### Collapsed
investor meetings 19, earnings call 10, unclassified 6, postal ballot 2, credit rating 1, press release 1, results 1, dividend 1

### Price / volume alerts
- 2026-11-12: CDSL +3.4% (Nifty +0.2%) - 2.0 sigma above its normal day after the market move (usual swing 1.6%); volume 3.3x its 20-day average (Volume at least 2.5x its 20-day average)
- 2026-11-11: CDSL +3.8% (Nifty +0.8%) - 1.8 sigma above its normal day after the market move (usual swing 1.6%); volume 3.3x its 20-day average (Volume at least 2.5x its 20-day average)
- 2026-11-06: IEX -2.4% (Nifty +2.0%) - 3.0 sigma below its normal day after the market move (usual swing 1.4%); volume 1.1x its 20-day average (Move unusual for this stock (2.5 sigma after the market))
  - Filed before this move: 2026-11-03 16:53 Announcement under Regulation 30 (LODR)-Press Release / Media Release
- 2026-11-06: MAPMYINDIA -4.3% (Nifty +2.0%) - 2.8 sigma below its normal day after the market move (usual swing 2.3%); volume 1.1x its 20-day average (Move unusual for this stock (2.5 sigma after the market))
  - Filed before this move: 2026-11-04 15:17 Announcement under Regulation 30 (LODR)-Press Release / Media Release
- 2026-11-05: BAJFINANCE +7.7% (Nifty +2.4%) - 3.0 sigma above its normal day after the market move (usual swing 1.3%); volume 3.5x its 20-day average (Move unusual for this stock (2.5 sigma after the market); Volume at least 2.5x its 20-day average)
- 2026-11-05: MARUTI +5.5% (Nifty +2.4%) - 2.8 sigma above its normal day after the market move (usual swing 1.2%); volume 2.6x its 20-day average (Move unusual for this stock (2.5 sigma after the market); Volume at least 2.5x its 20-day average)
- 2026-11-04: MAPMYINDIA +5.4% (Nifty +0.6%) - 2.1 sigma above its normal day after the market move (usual swing 2.2%); volume 11.5x its 20-day average (Volume at least 2.5x its 20-day average)
  - Filed before this move: 2026-11-04 15:17 Announcement under Regulation 30 (LODR)-Press Release / Media Release
- 2026-11-04: SUNPHARMA +0.2% (Nifty +0.6%) - 0.0 sigma below its normal day after the market move (usual swing 1.0%); volume 2.8x its 20-day average (Volume at least 2.5x its 20-day average)
  - Filed before this move: 2026-11-02 20:58 Rumour verification - Regulation 30(11)
  - Filed before this move: 2026-11-02 14:23 Clarification Sought From Sun Pharmaceutical Industries Ltd
- … and 5 more

Gemini use for this brief: gemini-3.5-flash-lite: 0 calls, 17 cache hits, 0 tokens · cost free tier (USD 0)
Built in 8.8 s. Sources refused on this connection: bse_api, nse_api. Filings come from screener's recent list and the BSE/NSE RSS store, so older or very busy days may be incomplete.

## 4. Alert rules: 90-day backtest across the portfolio

| Rule | Fires | Per week | Most frequent | Never fired |
|---|---|---|---|---|
| Move unusual for this stock (2.5 sigma after the market) | 58 | 3.2 | IEX 7, HAPPSTMNDS 6, HDFCBANK 5 | 0 |
| Volume at least 2.5x its 20-day average | 57 | 3.2 | HAPPSTMNDS 8, CDSL 7, MAPMYINDIA 6 | 1 |
| Unusual move (2 sigma) on heavy volume (1.8x) | 56 | 3.1 | HAPPSTMNDS 7, CDSL 5, IEX 5 | 0 |
| Price moved 5% or more | 34 | 1.9 | MAPMYINDIA 8, HAPPSTMNDS 7, BAJFINANCE 4 | 5 |

A 2.5-sigma rule would fire about 1.2% of days if returns were bell-shaped (about 20 times here); real returns have fatter tails, which is exactly why the backtest is shown before a rule is switched on.

## 5. Cost

This run (answers mostly reused from the cache): gemini-3.5-flash-lite: 0 API calls, 33 cache hits, 0 failed, 0 in / 0 out tokens. Cost: free tier (USD 0).

All Gemini use today, including the first time each filing was read: gemini-3.5-flash: 6 API calls, 1 cache hits, 4 failed, 1,262 in / 4,889 out tokens; gemini-3.5-flash-lite: 60 API calls, 100 cache hits, 0 failed, 94,183 in / 8,763 out tokens. Cost: free tier (USD 0).

Every model answer is cached by a hash of its exact input, so re-running a digest, or a second user holding the same stock, costs nothing.
