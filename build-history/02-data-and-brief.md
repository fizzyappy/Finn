# Part 2 · Data pipes and the push brief

[← Part 1](01-research-and-plan.md) · [Part 3 →](03-research-engine.md)

The push side of FINN answers one question for the investor: of everything my companies filed, what do I need to
know? This part covers how the data was proven, how filings are filtered and ranked, how results numbers are
verified, and how price alerts avoid being noise.

---

## 2.1 Proving the sources before building on them

The first engineering task was to make sure every source FINN depends on actually works, for any listed company,
from a normal machine. I asked the AI not to assume anything: every source had to be fetched live and checked.

**What we needed for any NSE company:**

- daily prices and the Nifty 50 index;
- financial statements (quarterly and annual results, balance sheet, cash flow);
- earnings-call transcripts and annual reports;
- exchange filings and the PDFs attached to them;
- the official list of NSE companies, so any company can be searched.

**How it was tested.** The AI ran each source live on five companies and wrote a validation report
(`backend/validation_report.md`). Prices were cross-checked against a second source, and the last close matched
within 0.13%. Only after that report did anything get built on top of the data.

**Small details that testing exposed.** These would have produced wrong numbers months later if they had not
been caught at the start:

- A quarter is matched to the same quarter a year earlier by its end date, not by its column position, because a
  missing column shifts everything.
- Growth percentages are withheld (with a reason) when the earlier figure is zero or negative. "Profit up 250%"
  from a loss is misleading.
- Banks and lenders are recognised from their own statement rows (interest, financing profit, bad-loan ratios)
  rather than from a list of names, so it works for any lender.
- Raw web pages are cached and parsed on every read, so a parser fix applies immediately instead of waiting for
  the cache to expire. We hit exactly this bug once, which is why the rule exists.
- A late daily price bar is filled from the live quote and marked provisional rather than silently guessed.

## 2.2 The first real obstacle: the exchange APIs

The BSE and NSE announcement APIs refused automated access with a "forbidden" response. One retry with ordinary
browser headers was blocked by my own machine's safety check as an attempt to get around bot protection.

This was a decision point. I chose to respect it completely: no retries, no workarounds, no browser
impersonation. The AI then designed a fallback that uses only sources published for programs to read:

- **The exchanges' official RSS feeds**, polled every five minutes into a local database, so FINN builds up its own
  history of filings.
- **A public list of recent filings per company**, used alongside the feeds.
- **Every brief records which sources worked for which company**, so a gap is visible to the user rather than
  silently missing.

The trade-off was logged honestly: the feeds hold only the newest items, so a very busy day can be missed between
polls, and history before the poller started is thinner. In return, FINN can say "primary sources only" without
any asterisk. Later, when the daily data refresh ran from GitHub's servers, the exchange API answered from there,
and the pipeline used it where it worked while keeping the feed-based fallback for everything else.

## 2.3 Filtering: teaching FINN what a filing is

**The approach.** Rules first, AI second. From our earlier analysis we already had the idea of ordered rules with
sub-types and a base score per category. The AI rewrote the rules against real filings rather than imagined ones,
because the real subjects are messy: a "concall update" is a meeting notice, not a results call; a bank files its
results under "board meeting outcome".

**How it was built and measured.**

1. We labelled 90 real filings from the 18 holdings by hand into the challenge's 17 categories, plus how each
   should be treated (headline card, one-liner, or collapsed as routine).
2. Ordered rules were written and tested against that set.
3. Where no rule is confident, Gemini's fast model reads only the first page of the filing and picks a category.
4. To check the rules weren't just memorising the labelled set, we ran a blind test on 34 other companies.

**Results.**

| Test | Rules alone | Rules + AI |
|---|---|---|
| Category, 90 labelled filings | | 100% |
| Treatment (card / one-liner / collapsed) | | 98% |
| Category, blind set of 34 other companies, first pass | 53% | 82% |

The important part is how little AI this needed: the blind-set improvement cost 15 model calls. Most filings are
classified by rules and never reach the model at all.

## 2.4 Ranking: how much should this interrupt you?

Every filing gets a materiality score:

> category base score × event details × size of the holding × the investor's preferences + a bonus if the stock
> moved unusually around the filing

**Why each part exists:**

- **Event details:** a CEO resigning is not a company secretary resigning; an order worth a large share of market
  cap is not a routine order.
- **Holding size:** a filing from a 10% holding matters more than one from a 2% holding.
- **Preferences:** the investor can boost, mute or tune any type of announcement.
- **Market reaction:** if the stock moved unusually that day, the filing gets a bonus, because the market is
  telling you it mattered.

Thresholds: a score of 0.6 or more becomes a headline card, 0.3 or more a one-liner, and everything else is
collapsed (never deleted).

**Why every factor is kept.** The score is returned with all its parts, so the app can answer "why am I seeing
this?" for any card. That became the **Why?** button: tap it and the card flips to show each factor and how much
it contributed. In a product built on trust, an unexplained ranking would undo everything else.

The weights are hand-set rather than learned, and that trade-off is logged. With a few weeks of user feedback,
swipes ("less like this") already adjust a category's weight, and the investor can reset it in Settings.

## 2.5 Verifying results numbers: the AI reads, Python checks

Quarterly results are the most important filing type, and the one where a wrong number does the most damage. The
approach was designed so the AI can never be the last word on a number.

**How a results card is built:**

1. Find the results filing (or the investor presentation filed after the quarter).
2. Locate only the pages that contain the results table and send just those pages to the model. This keeps cost
   down and stops the model reading the wrong table.
3. The model reads the table and returns the figures in a fixed format.
4. Python checks the figures:
   - three periods line up (this quarter, the previous quarter, the same quarter a year earlier);
   - profit before tax minus tax equals profit after tax;
   - totals add up;
   - units are consistent;
   - the figures match a second source to the crore.
5. Only if every check passes does the card show **Verified**, and the user can open the list of checks.

**What testing caught, and the general rule each produced:**

| What happened | The rule it produced |
|---|---|
| ITC's reported revenue included excise duty | Excise is netted out before comparing |
| Small companies report half-yearly, not quarterly | Half-year periods are recognised and compared correctly |
| Some results PDFs are scanned images with no text | Short scanned filings go to the model as page images |
| A company printed the columns in an unusual order | Column order is detected from the period headers |
| An AI headline quoted standalone profit while the card showed consolidated | Results headlines are written by Python from the verified figures |
| One unreachable PDF cost a company its card | Up to three exchange-filed documents are tried before giving up |

If the checks fail, the card says "Results filed · numbers not verified" and links the filing. A wrong number is
worse than no number.

## 2.6 Summaries that cannot invent things

Non-results filings get a short headline and one-line summary. Live runs showed the model could embellish: it
described a credit rating that was "reaffirmed, outlook revised to positive" as an upgrade. So every summary now
passes checks before it is shown:

- every number in the summary must appear in the filing;
- praise words must come with an amount;
- action words such as "upgrades" or "acquires" must appear in the filing itself;
- fixed formats (dividends, rating actions) use templates instead of free text.

If a summary fails, FINN falls back to a cleaned version of the filing's own subject line.

**People cards.** For management changes, FINN quotes the person's background from the filing itself (SEBI
requires a brief profile there), and every quoted line must be found word for word. We deliberately did not
scrape professional networking sites, both for their terms of use and to stay with primary sources.

## 2.7 Alerts that are not noise

A 3% move is noise for a small company and a big event for a utility. So FINN judges each day against the
stock's own normal:

- the day's move after taking out the market's move (the Nifty, adjusted for the stock's sensitivity to it);
- expressed in units of the stock's usual daily swing;
- together with volume against its 20-day average.

**How the default was chosen.** We did not guess. A 90-day backtest across the 18 holdings showed:

| Rule | Alerts in 90 days | About per week |
|---|---|---|
| Move above 2.5× the usual swing | 58 | 3 |
| Move above 3× the usual swing and volume above 2.5× average (chosen default) | 21 | 1 |

Three pings a week is noise; one a week is worth reading. The investor can change the rule in the app and
immediately see how often it would have fired over the last 90 trading days, with each alert day drawn as a peak.

**Timing, not cause.** If a company filed something before an unusual move, FINN shows it as "filed before this
move". It never claims the filing caused the move, because timing is a fact and cause is not.

## 2.8 The digest

The brief brings everything together for a chosen time window (since the last visit, 24 hours, 3 days, 7 days or
a custom range):

- **Needs your attention:** the headline cards.
- **Worth knowing:** one-liners.
- **Unusual moves:** price and volume alerts, with any filing that came before them.
- **Collapsed:** routine paperwork grouped by type, one tap to expand.

Every brief records which data sources worked, and the whole thing is built in Python from cached model answers,
so rebuilding it costs nothing for filings already read.

---

Next: [Part 3 · The research engine](03-research-engine.md)
