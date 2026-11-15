# Part 2: Real data and the push engine (the brief)

This part covers how FINN gets its data and how it turns a day of exchange
filings into a short brief that an investor can finish in under a minute. It is
written from my side of the build. The lines starting with ">" are my everyday
instructions to Claude, tidied up but kept to what I actually asked. The lines
starting with "●" are what Claude did, found or recommended in response, and
what I decided.

The thread running through this part is one rule I set before any code existed:
the model reads, Python decides. Every number is computed in Python. Every quote
is checked word for word. Every ranking can explain itself.

---

## 2.1 Prove the data before building on it

> before building anything on the data, test it. check every source live on real
> companies that are very different from each other and tell me in simple words
> what works, what breaks and what changes in the plan

● Claude wrote small test scripts ("spikes") instead of starting the engine,
  because I asked to find the risky parts on the first afternoon rather than on
  the last night. Each spike tested exactly one question against live sources:
  can we get announcements, can we get prices, can we get financial statements,
  can we get results PDFs and transcripts, and can Gemini read them.

● It picked a deliberately mixed set of companies so the tests would not be
  flattering: Reliance (huge and complex), Infosys (IT services, guidance in
  constant currency), HDFC Bank (a bank, so a different statement layout),
  Suzlon (volatile, profit swinging) and RateGain (small, fast-growing).

● Prices: yfinance returned a full year of daily bars for every company. Claude
  cross-checked the latest close against Screener's quoted price and the gap was
  a few hundredths of a percent for all five (for example Reliance 1,339.70 vs
  1,340.00).

● It found one quirk I would never have spotted myself: Yahoo sometimes
  publishes the latest daily bar late. Claude's recommendation was to fill that
  last bar from Yahoo's live quote and mark it "provisional" instead of silently
  losing a day. I agreed, because a missing day would make the alert engine
  think nothing happened.

● Financial statements: Screener's company pages gave quarterly and annual
  tables (revenue, operating profit, PBT, PAT, EPS) for all five. Banks came
  back with a different layout, which Claude flagged early because it meant the
  results card would need a bank version later.

● Results PDFs and transcripts: reachable from the exchange sites for most
  companies. For Infosys and Suzlon, the results PDF was not reachable from my
  machine that day. Claude recorded it as a known gap instead of hiding it, and
  the later design (try up to three exchange documents per card) came from this.

---

## 2.2 The exchanges said no

> filings should come straight from the exchanges. start with bse and nse
> announcement apis

● Both APIs returned HTTP 403 to scripted requests. Claude stopped and explained
  what that meant: the exchanges are deliberately blocking bots, and the only
  ways around it are tricks that make a script pretend to be a browser.

● I asked what the options were. Claude laid out three: work around the block,
  pay for a data feed, or combine sources that are published for programs to
  read.

> no workarounds. if the exchange is blocking bots we respect it, its not a
> puzzle to solve. find the way thats meant for programs and write down what it
> costs us

● My reasoning was simple. FINN is an investment app whose whole pitch is trust.
  If its data pipeline starts by getting around a stock exchange's access rules,
  that trust is gone before the first screen. Claude also tried exactly one
  retry with standard browser headers; the safety check on my laptop refused it
  as bot-check circumvention, and I told Claude to treat that refusal as final
  and not pursue it further.

● The honest route Claude found and built:
- BSE and NSE both publish official RSS feeds of corporate announcements. These
  exist precisely so programs can read them. A poller reads both every five
  minutes into a local SQLite store.
- Screener's recent-announcements list on each company page fills in items from
  before the poller started.
- Company PDFs are fetched only from exchange sites, or from company websites
  when the company's own document list links to them. This also stops the
  backend from being used to fetch arbitrary URLs.

● The cost went into DECISIONS.md, because I had asked Claude to log every
  trade-off: the RSS feeds hold only the newest 25 or so items, so a very busy
  hour could be missed between polls, and the full 7-day history is only
  guaranteed once the poller has been running for a while. Every brief now says
  which sources worked and which refused, so this is never hidden from the user.

● When Claude reported back at the end of this step, it gave me real numbers for
  the five test companies (latest quarter, ₹ crore):

| Company | Last close | Revenue YoY | Profit YoY |
|---|---|---|---|
| Reliance | 1,339.70 | +29.8% | +33.8% |
| Infosys | 1,141.50 | +10.7% | +6.3% |
| HDFC Bank | 804.00 | +9.4% | +5.8% |
| Suzlon | 38.25 | +26.0% | −69.2% |
| RateGain | 674.90 | +152.5% | +47.1% |

● Every closing price matched Screener's within 0.13%. HDFC Bank was correctly
  treated as a bank, so it showed no misleading EBITDA. Claude downloaded and
  read real transcripts (Infosys 48 pages, Reliance 29 pages) and 34 automatic
  checks passed. It also found and fixed three real problems: Yahoo hadn't
  posted Friday's price yet (now filled in and marked provisional), a
  "transcript" filing that was really a one-page cover letter (now skipped), and
  some company websites refusing downloads (now allowed only when the company's
  own document list points there).

● In the first live run, the RSS poll pulled 1,692 BSE items and 362 NSE items,
  and the brief said honestly: "Sources refused on this connection: bse_api,
  nse_api. Filings come from screener's recent list and the BSE/NSE RSS store."

---

## 2.3 Small data rules that prevent big mistakes

> wrong number is worse than no number. go through the whole data path and find
> every place a number can go wrong quietly, and fix each with a rule not a
> patch

● Claude went through the data path looking for places where a number could be
  silently wrong, and turned each one into a rule. I liked that these were
  general rules, not fixes for one company.

● Quarter matching: a quarter is matched to the year-ago quarter by its
  period-end date, not by counting columns. If Screener is missing one column,
  counting would shift every comparison by a quarter and every YoY number would
  be wrong without any error.

● Negative bases: growth % is withheld, with a short reason, when the base is
  zero or negative. A "+250% profit" headline that comes off a loss is
  technically true and completely misleading. Suzlon's numbers were the case
  that made this obvious.

● Banks: banks and NBFCs are detected from the labels in their own statements
  (financing profit, NPA) rather than from a hard-coded list of names, so it
  works for any lender, including ones we never tested.

● Quotes: extracted PDF text is stored exactly as extracted and only normalised
  when searching, so a quote shown to the user can always be found in the
  original.

● Caching: raw pages are cached, but parsed fresh on every read. Claude made
  this change after we hit a bug where a parser fix did not show up because the
  old parsed result was still cached. The rule means a fix takes effect
  immediately.

● Company list: the list of companies comes from NSE's own EQUITY_L.csv, which
  is a primary source, covers every NSE company and gives the ISIN. The BSE code
  comes from Screener.

---

## 2.4 What the brief is trying to do

> brief should be something you finish, not a feed you scroll. rank by what
> matters to my money, not whats loud in the market. and every card should be
> able to tell why its there

● Before writing the engine, Claude and I agreed on the pipeline in plain words:
  collect every filing for my holdings, decide what type of filing it is, score
  how much it matters to me, decide how loudly to show it, link it honestly to
  the price, and explain the ranking.

```
filings (RSS + Screener)
   -> classify into 17 types (rules first, Gemini only if unsure)
   -> materiality score (Python, every factor kept)
   -> treatment: hero card / one-liner / folded into routine
   -> price link ("filed before a move", never "caused")
   -> Why? card shows every factor
```

● The output of the first live run on my demo portfolio of 18 holdings, last 7
  days: 21 filings, 4 that matter. That ratio is exactly the point of the
  product. Twenty-one things happened, and FINN tells you that only four are
  worth your attention.

---

## 2.5 Classifying every filing into 17 types

> cover all 17 announcement types. rules first because they are free and you can
> explain them, model only when rules arent sure. and check accuracy on real
> filings labelled by hand, not examples we make up

● ENAM's brief lists 17 announcement types: results, management change, credit
  rating, order wins, fund raises, M&A, dividends, investor meetings and so on.
  Claude proposed rules first, because keyword rules are fast, free, explainable
  and easy to test.

● The first rules Claude wrote from the category names alone missed a lot. Real
  subject lines are messy. For example, a filing titled "Con. Call Updates" is a
  meeting notice, not a results call, and HDFC Bank files its results under
  "Board Meeting / Outcome of Board Meeting" rather than under "Result". So
  Claude rewrote the rules against 90 real filings from my portfolio, labelled
  by hand.

● When no rule recognises a filing, Gemini Flash-Lite reads page 1 of the PDF
  and picks the type. This keeps model calls rare: most filings never reach the
  model at all.

● Results on the hand-labelled sets:

| Set | Filings | Category correct | Treatment correct |
|---|---|---|---|
| My portfolio, rules + Gemini | 90 | 100% | 98% |
| Other companies, rules only | 34 | 82% | - |
| Other companies, rules + Gemini | 34 | 100% | - |

● I asked Claude to be honest about these numbers, and it was. The rules were
  written after seeing the portfolio set and adjusted after a first pass on the
  other-company set, where rules alone got 53% and rules plus Gemini got 82%. So
  the final numbers are in-sample. That caveat is written in the report rather
  than buried.

● The two remaining disagreements with my labels were both HDFC Bank: a postal
  ballot outcome and a management change that I had marked as one-liners and the
  engine scored just under the one-liner line (0.19 and 0.297). These are
  judgement calls rather than errors, and I left them.

---

## 2.6 Summaries that cannot lie

> no made up summaries at all. if the filing doesnt say it, the card cant say it

● The first live run produced a summary saying ICRA had upgraded Suzlon's
  rating. The filing actually said the rating was "A+ reaffirmed; outlook
  revised to Positive". For an investor, an upgrade and a reaffirmation are
  completely different stories.

● Instead of patching that one case, I asked Claude to make it a general rule,
  and it became four rules:
- every number in a summary must appear in the filing itself;
- any action word (upgrade, downgrade, acquire, appoint, resign) must be the
  filing's own word;
- praise words ("strong", "robust", "record") need an amount behind them;
- formats that are always the same, such as credit ratings and dividends, use
  fixed templates instead of free text.

● If a summary fails any check, the card falls back to a cleaned version of the
  filing's own subject line. A plain but true line is better than a fluent wrong
  one.

● Screener's own one-line "detail" text for each announcement is used only to
  help classify, never shown to the user, because it is Screener's summary and
  not the filing.

---

## 2.7 Materiality: ranking by my money

> score it from my holding and keep every part visible. if something is on top i
> want to see why in one tap

● Claude built the score in Python from parts, and every part is stored
  separately so the app can explain itself:

```
materiality = base score for the announcement type
            x modifiers from the filing (e.g. size of an order)
            x weight of my holding
            x my preference for this type (Mute / Normal / Boost)
            + bonus if the market reacted unusually that day
```

● Thresholds: 0.6 and above becomes a hero card, 0.3 to 0.6 becomes a one-liner,
  and anything below 0.3 is folded into a "routine" line at the bottom (for
  example "investor meetings 10, press release 2").

● The Why? on each card shows those exact parts. For the top card in the first
  run, Bajaj Finance's QIP, it read: fund raise / equity (0.72); holding weight
  6.0% (1.02); stock moved unusually the next day: +3.4% (+2.2 sigma vs its
  normal), volume 1.2x. Total 0.834.

● The weights are hand-set rather than learned from data. Claude flagged that as
  a limitation and it is in DECISIONS.md; with no labelled history of what
  investors actually clicked, there was nothing honest to learn from.

---

## 2.8 Linking filings to the price, honestly

> show how the stock reacted but never say the filing caused it. we say timing,
> not cause

● Cards say a filing was made before a move of a certain size, for example
  "Filed before a +11.6% move". They never say the filing caused the move.
  Timing is a fact. Cause is not.

● The reaction is measured relative to the Nifty, so a day when the whole market
  rose 1.7% does not make every stock look like it reacted to its own news.
  Reliance's +11.6% on a day the Nifty did +1.7% was 9.0 times its usual move
  after the market's effect, on 5.8x its normal volume, and it came right after
  its earnings call transcript was filed.

---

## 2.9 The results card and its eight checks

> results card is the one people trust most so be paranoid. model only reads the
> table, python does all the maths and checks, and if its not verified the card
> should say so

● Claude designed the results card so the model's only job is to read numbers
  off the page, and Python does everything else.

● To save tokens, the model is shown only the pages containing the results
  table, cut into a small PDF, not the whole filing. A full results PDF was
  around 12,000 input tokens; the table pages are a fraction of that.

● Python then runs eight checks on every card:

| # | Check | Why it exists |
|---|---|---|
| 1 | Three periods present (this quarter, last quarter, year-ago) | QoQ and YoY need all three |
| 2 | PBT minus tax equals PAT | Catches misread rows |
| 3 | Line items add up to totals | Catches skipped rows |
| 4 | Units consistent (lakh vs crore) | A 100x error looks plausible |
| 5 | Right quarters compared, by date | Columns are sometimes printed out of order |
| 6 | Values within sane bounds | Catches decimal slips |
| 7 | Consolidated and standalone not mixed | They tell different stories |
| 8 | Matches Screener | An independent second source |

● Pass all eight and the card says "Verified 8/8". Fail one and it says "Results
  filed, numbers not verified" instead of showing a number we are not sure of.

● What the checks caught on live runs:
- ITC's revenue included excise duty, so growth looked wrong against Screener.
  Fix: revenue is netted of excise.
- Some small companies report half-yearly, not quarterly. Fix: the card handles
  half-year periods instead of assuming quarters.
- One PDF printed its columns out of order. Fix: periods are matched by their
  date labels, never by column position.

● The headline problem. In one run the model's one-line summary quoted
  standalone profit while the card itself showed consolidated profit. Both
  numbers were real, but the card contradicted itself. I asked for a general
  fix, and Claude's was: the model no longer writes the headline of a verified
  card at all. Python writes it from the card's own numbers, for example "ITC
  results: PAT Rs 4,229 cr, -18.5% YoY".

● Scanned filings. Some results PDFs have no text layer at all (they are
  images). Gemini can read page images, so scanned filings under 25 pages are
  sent whole. Happiest Minds' results were verified this way, 8/8, with "pages:
  all (no text layer to locate the table)" shown on the card.

● Banks. EBITDA means nothing for a bank. Claude built a separate bank card from
  the statement tables only: total income, net interest income (interest earned
  minus interest paid, computed in Python), an approximate interest margin that
  is labelled as approximate, bad loans where reported, and deposits. CASA ratio
  and the credit-deposit ratio are not in the tables, so the app lists them as
  missing instead of guessing. I chose that over pulling them from somewhere
  unverified.

● One-off items. In an early test, TCS's quarter included a ₹668 cr one-off
  legal settlement, which made the quarter-on-quarter comparison misleading. If
  the "exceptional items" line is not zero, Python flags it on the card. No
  model judgement is involved in deciding what counts as one-off.

---

## 2.10 Management changes

> when someone in management changes, tell me who the new person actually is,
> from a primary document

● Claude's first suggestion for the background of a new executive was to look
  them up on LinkedIn. I said no: scraping LinkedIn breaks the site's terms, and
  SEBI already requires a short profile of the person in the filing itself.

● So the card quotes the background from the filing, with the page number, and
  the quote must be found word for word in the filing or it is dropped. If a
  company files only a thin profile, the card is thin too. That is a fair trade
  for never showing something unverified.

---

## 2.11 Alerts that respect each stock

> 3% move means nothing alone. alerts should judge each stock against its own
> normal, after taking out the market

● This was one of the ideas that came from pushing back on the first feature
  list. A fixed "alert me at ±3%" rule is wrong both ways. For a stable
  large-cap, 3% is real news. For a volatile small-cap, 3% is an ordinary
  Tuesday.

● Claude's method:
1. For each stock, compute its usual daily move after removing the market's
   effect: the stock's move minus the Nifty's move scaled by the stock's
   sensitivity to the Nifty (beta).
2. Express each day's move in multiples of that usual move ("sigma").
3. Compare volume with that stock's own 20-day average.

● This means a market-wide fall does not fire 18 alerts at once, and a quiet
  utility moving 3% is treated very differently from a small-cap doing the same.

> dont set the default by feel. backtest the rules on real history and pick the
> one that fires rare enough to deserve a notification

● Claude ran a 90-day backtest across the 18 stocks in my demo portfolio and
  compared five candidate rules:

| Rule | Fired | Per week |
|---|---|---|
| Move 2.5x its usual (after the market) | 58 | 3.2 |
| Volume 2.5x its 20-day average | 57 | 3.2 |
| Move 2x usual on 1.8x volume | 56 | 3.1 |
| Price moved 5% or more | 34 | 1.9 |
| Move 3x usual AND volume 2.5x | 21 | 1.2 |

● Three alerts a week is too many for something that buzzes your phone; people
  learn to ignore it. About one a week feels like news. So the combined rule (3x
  usual move and 2.5x volume) became the default.

● The backtest also showed something useful on its own: the obvious 2.5-sigma
  rule would fire about 20 times in that period if stock returns were
  bell-shaped, but it fired 58 times. Real returns have fat tails. That is
  exactly why a guessed threshold would have been wrong.

● In the app, the slider in settings still shows each stock's plain-percentage
  equivalent, so the threshold never feels abstract, and the backtest re-runs
  instantly in the browser on 120 days of exported measures as you drag it.

● Three real alerts from the 14-day window in the first run: Bajaj Finance +7.7%
  (3.0x its usual move, 3.5x volume), Reliance +11.6% (9.0x, 5.8x volume) and
  Dixon +12.0% (6.0x, 6.0x volume).

---

## 2.12 Mute, Normal, Boost

> give the investor control over noise, for each type let them mute, keep normal
> or boost

● Each of the 17 announcement types can be set to Mute, Normal or Boost. Boost
  raises an item's materiality, Mute folds it away. It is the fifth thing an
  investor needs from the app, and it sits in settings where it belongs rather
  than on the main screen.

● (The look and feel of this control came much later, in the design rounds. See
  Part 4.)

---

## 2.13 What it cost

> every model call is a cost. cache by content so we never pay twice, and log
> usage on every call

● Every model answer is cached by a hash of its exact input. Re-running a brief,
  or a second user holding the same stock, costs nothing.

● On the day of the first full live run, including the first time every filing
  was read: Flash-Lite made 134 API calls with 388 cache hits; Flash made 6
  calls. Re-running the 14-day brief afterwards made zero API calls and 17 cache
  hits. Total cost: zero, on the free tier.

● Flash (the stronger tier) often timed out that day, 4 of 10 calls. The router
  fell back to Flash-Lite and labelled the answer, so the pipeline kept moving.
  This is in DECISIONS.md as a known cost: some second attempts are answered by
  the lighter model.

---

## 2.14 What Claude reported at the end of the push engine

● When the push engine was done, Claude ran it live on my 18 stocks and reported
  back in plain words. Over 14 days, 73 filings came in and FINN judged 16 of
  them important, folding the rest into counts like "19 investor-meeting
  notices". Real examples from my brief:
- an ITC results card, verified 8/8: revenue ₹20,269 cr (+3.9% YoY), EBITDA
  −15.1%, profit −18.5%, matching Screener exactly;
- a Bajaj Finance fund raise at ₹992.25, with its "why" shown: a fund raise, my
  6% holding, and a 2.2× normal move the next day;
- a price alert: "IEX −2.4% while the Nifty rose 2.0%: about 3× its normal day";
- a people card quoting a new director's background word for word from the
  filing, with page numbers.

● Cost so far: $0, from 66 AI calls on the free tier.

● It also told me the safety rules on my laptop had stopped one approach to
  BSE's filing system, and that it was leaving that alone, since the official
  feeds plus Screener worked well.

## 2.15 What I took away from this part

● The data work is where most investment apps quietly cut corners, and it is
  where I spent my "no" most often: no bypassing the exchanges, no LinkedIn
  scraping, no model-written numbers, no guessed thresholds.

● Every time the AI made a mistake in this part (the "upgrade", the standalone
  headline, the excise revenue), I asked for a rule that fixes the whole class
  of mistake, not a patch for one company. That is why the engine got better as
  it saw more data instead of collecting special cases.

● Measuring instead of guessing turned out to be the cheapest decision of all. A
  backtest of 90 days took minutes and gave a default I can defend in one
  sentence.

Next: Part 3, the research engine (promise ledger, dodged questions, bull and
bear).

