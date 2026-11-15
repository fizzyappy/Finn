# How FINN was built

FINN's logo, the slanted "F", and its visual identity were designed by me. Everything else in this document
describes how I worked with AI to turn a brief into a product: what I was trying to achieve at each stage, why
each decision was made, how we tested it, what testing showed was missing, and how we fixed it.

I used **Claude Code** as the engineering agent: it planned, wrote and ran the code on my machine, tested against
live data and reported back. I owned the direction, the product judgement and the design. Inside the app, Gemini
is used only where rules cannot do the job.

The full detail is in the five parts listed in this folder's README.

---

## 1. Framing the problem before writing code

The first step was to decide what the app should be for, not what it should contain. An investor holding 15–20
Indian stocks receives dozens of exchange announcements a week, and almost all of them are routine paperwork.
Showing more information is not the problem to solve; deciding what deserves attention is. That made **filtering
and ranking** the core of the push side of the app.

The second insight was on the pull side. Results are available everywhere, but very few tools check whether
management delivered what it promised on earlier earnings calls. That gap became FINN's signature feature: a
**promise ledger** that measures each stated target against what the company later reported.

Because this is a finance app, trust had to be designed in from the start. I set a small number of rules before any
code was written, and every later decision was checked against them:

- Use primary sources only: exchange filings, earnings-call transcripts and annual reports.
- Let rules do the work first; use the AI only where rules cannot.
- The AI may read and phrase. Python does every calculation and every verdict.
- A quote is shown only if it is found word for word on the page it cites.
- Every AI call is cached and its cost recorded.
- Never work around a website's bot protection.

The work was then split into six tasks (setup, data pipes, push engine, pull engine, app, submission), each of
which had to end with something running on live data and a written report I could check.

## 2. Proving the data before building on it

A product built on unverified data cannot be trusted, so the data layer came first and was tested live on five
companies before anything was built on it. Prices were cross-checked against a second source and matched within
0.13%.

The first real obstacle appeared here: the BSE and NSE announcement APIs refuse automated access. Rather than look
for a way around that, I chose to respect it, and we designed a fallback that uses only sources meant for programs
to read: the exchanges' official RSS feeds, polled continuously into a local database, plus a public list of recent
filings. Each brief records which sources worked for which company, so a gap is visible instead of silent. This
decision is why FINN can honestly say it uses primary sources only.

Testing at this stage also exposed details that would have produced wrong numbers later: matching a quarter to the
year-ago quarter by its end date instead of its column position, withholding growth percentages when the base is
zero or negative, and recognising banks and NBFCs from their own statement rows rather than from a list of names.

## 3. The brief: filter, rank, verify

**Filtering.** To teach FINN what a filing is, we labelled 90 real filings by hand into the challenge's 17
categories and wrote ordered rules against them. The AI is consulted only when no rule is confident, and only reads
the first page. This kept cost and error low: the rules alone classify most filings, and on a blind set from 34
other companies accuracy rose from 53% with rules alone to 82% with the AI as a fallback.

**Ranking.** Each filing gets a materiality score built from its category, the specifics of the event (a CEO
leaving is not the same as a company secretary leaving), the size of the holding, the investor's preferences, and
whether the stock moved unusually. Every factor is kept, so the app can always answer why something is on screen.

**Verification.** For results, the AI reads only the results-table pages. Python then checks that the periods line
up, that profit before tax minus tax equals profit after tax, that totals add up, that units are right, and that the
figures match a second source. Only then is a card marked verified. Testing surfaced cases that each became a
general rule: revenue that included excise duty, companies that report half-yearly, scanned PDFs with no text,
columns printed out of order, a summary that mixed standalone and consolidated profit (headlines are now written by
Python), and a summary that described a reaffirmed rating as an upgrade (action words must now appear in the
filing).

**Alerts.** A 3% move means different things for different stocks, so each day is judged against the stock's own
usual move after removing the market's move, together with volume against its recent average. The default rule
was chosen by backtesting 90 days of data: the obvious threshold would have alerted about three times a week, the
chosen one about once. Filings before a move are shown as preceding it, never as causing it.

## 4. Research: does management keep its word?

For any company, FINN reads the last five earnings calls, extracts every target management set, resolves its
deadline in Indian financial years, measures it against the reported numbers, and records a verdict with the exact
quote and page.

To know whether this could be trusted, we checked it by hand. Extraction was correct for all 45 statements tested,
but only four of seven verdicts were right at first. The cause was instructive: a margin target for one business
segment had been compared with the margin of the whole group. The fix was general rather than specific: every
promise now carries its scope, and only company-wide targets are judged against company-wide numbers. Targets set in
constant currency or US dollars are marked as not measurable rather than converted, and a target is called quietly
dropped only after two later calls with no mention of it. After these changes all checked verdicts were correct.

The same approach was applied to the question of whether management answers analysts. The first version treated a
request for clarification as a dodge, so the rule was tightened: a question counts as dodged only when the quoted
answer itself shows the refusal, and the flags on one company were then confirmed by hand.

Analysis follows the same principle of Python deciding and the AI phrasing. A one-line summary at the top of each
company, the facts behind the bull and bear case (growth slowing against its trend, margins squeezed, a one-off
jump confirmed by share dilution), and the sentence above each chart are computed by Python. The AI only words
bullets from numbered facts, and any bullet whose numbers do not match its facts is discarded. Questions asked in
the app are answered only from the company's cited evidence. For lenders, the app shows bank measures from the
statements and states plainly which ones the statements do not contain.

## 5. The app: making trust easy to see

The app is a phone-first progressive web app that can be installed on a home screen. It ships with a snapshot of
real outputs so the link always works, and uses a live research engine for companies outside the snapshot.

Every change was verified automatically: each screen was captured at phone size and checked for errors,
accessibility, colour contrast and layout overflow, and the full set was re-run after almost every change.

The interface was shaped through short review loops on my phone. Each round I identified what felt wrong as a user
and the AI implemented and re-tested the change. The main design decisions that came out of this:

- The first screen is never empty: on a quiet day it says so in one line and shows what mattered that week, with a
  funnel showing how many filings were reduced to how many worth knowing.
- Every card answers the investor's next question: how large the holding is, why it is shown, whether its numbers
  are verified, and a direct way to clear it or open the company.
- A calm visual system: a plain dark background, one restrained accent colour, a lighter wordmark, my logo, and a
  short opening animation in which the F assembles itself.
- Navigation that explains itself: labelled tabs, a section jump bar on long pages, and smooth transitions.
- Visuals that carry meaning: recent years highlighted against older ones, values on tap, alert days drawn as peaks
  whose height reflects the size of the move, and cash earned per rupee of profit drawn against a one-rupee line.
- Features that did not earn their place were removed, such as reading the brief aloud.

Near the end, I used an independent critical review of the app. Rather than applying every suggestion, we ranked
them by what a reviewer would notice first, what the challenge explicitly asks for, and what was safe to change
before submission. One suggestion, checking vague directional promises, was deliberately postponed because doing it
properly would have meant adding verdicts that had not been checked by hand.

## 6. Deployment and fallbacks

The app is hosted on Vercel and the research engine on Render's free tier. After deployment, the live server was
tested end to end: health, a company already in the snapshot, a company never seen before (read live in about five
minutes) and the question box.

Free infrastructure fails in predictable ways, so each failure has a fallback:

- If the research server is asleep, the app waits and says so instead of failing.
- If another company is being read, the app shows its place in the queue.
- If a data source fails for one company during the daily refresh, that company keeps its previous data.
- A small committed seed of cached answers means a restarted server does not repeat paid work.
- Only the app itself may call the server, and each visitor is rate-limited, so the shared AI quota cannot be
  exhausted.
- A scheduled job rebuilds the data every weekday without my laptop, and it was run once by hand to confirm it
  works from the cloud.

Testing after deployment also found gaps that were then closed: a misleading empty first screen, cost figures that a
fresh cloud run had reset, and an automated check that had stopped halfway without reporting it.

## 7. How the AI was used

- **Claude Code** handled the engineering: planning, code, live runs, tests, screenshots, accessibility checks,
  commits and deployment checks. I set priorities, judged the product and directed the design.
- **Gemini** runs inside the app through one router with a fast tier and a stronger tier, automatic fallback, a
  cache keyed on the exact input, and a log of every call. The whole build used about 400 model calls and one
  million tokens, with roughly two thirds of requests answered from cache, at no cost on the free tier.
- **Evidence over claims:** 119 offline tests, hand checks of promises and dodged questions, a 90-day backtest for
  alerts, and automated checks of every screen.

## What the AI got wrong, and how it was caught

| Mistake | Caught by | Fix |
|---|---|---|
| Compared a segment's margin target with the group's margin | hand check | every promise carries its scope |
| Described a reaffirmed credit rating as an upgrade | summary checks | action words must appear in the filing |
| Misread a CEO as a page header and a CFO as an analyst | live runs | roles taken from introductions and question-and-answer behaviour |
| Treated a clarification as a dodged question | hand check | stricter judge plus a Python evidence rule |
| Listed a neutral count as a bull point | review | Python comparison facts tied to a side |
| Built an alternative I had not asked for | my review | removed; options are proposed, not built |
| Reported a clean test run that had stopped halfway | its own follow-up check | test fixed and every check re-run |

The full history of changes is in the repository's commit log.
