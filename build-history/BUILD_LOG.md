# How I built FINN with AI: the full working log

This is the step-by-step story of how I built FINN with **Claude Code** as my engineering partner: what I asked
for, how I pushed back, what we tested, what broke, what we found was missing, and why every decision was made.
It is written the way we actually worked: short, direct instructions from me, and the AI doing the engineering,
testing and reporting in plain language.

I designed FINN's logo (the slanted "F") and steered every product and visual decision. Claude Code wrote and
tested the code. Gemini (free tier) is the only model *inside* the app, and it is used only where rules cannot do
the job.

My working rules for the AI, from the very first message:
- "I don't want a fast app, I want a great app that can actually stand out."
- "Do the work yourself, don't make me do it." (Claude Code ran the code, the tests and the checks on my PC.)
- "Explain everything to me in plain words." (Every update came as: what was done, what changed, what I must do.)
- Ask me before installs, accounts, commits or pushes; never put my API key anywhere it could leak.

---

## Part 1 · Setting the foundation

### Step 1: Read the brief like an investor, not like a coder
**What I asked:** read the challenge, tell me what the deliverables really are, and what would make this stand out
among the best submissions.

**What we worked out together:**
- An investor with 15–20 stocks does not need *more* information. Indian companies file dozens of announcements a
  week, and almost all of them are paperwork. **The product is the filter.**
- The second thing nobody does well: *does management keep its word?* Results are everywhere; checking last year's
  promises against this year's numbers is not. **That became FINN's signature feature: the promise ledger.**
- In finance, **trust is the product.** One wrong number and the reviewer stops believing everything else.

**The rules we wrote down before any code** (they are in `CLAUDE.md` and `DECISIONS.md`):
1. Primary sources only: exchange filings, earnings-call transcripts, annual reports.
2. Rules first, AI second. The AI may *read*; Python does every calculation and every verdict.
3. Every quote must be found word for word on the page it cites, or it is dropped.
4. Every AI call is cached and its cost logged.
5. No tricks to get around a website's bot protection, ever.

### Step 2: The plan
Claude broke the challenge into six tasks: setup → data pipes → push engine (the brief) → pull engine (research)
→ the app → submission. Each task had to end with something running on **live data** and a report I could read.
I approved the plan and said: keep going on your own, and keep checking whether there is a better way to do each
part.

---

## Part 2 · Data pipes: prove every source is real

### Step 3: Build the data layer and test it live
For any NSE company we needed prices, financial statements, earnings-call transcripts, exchange filings and the
filing PDFs themselves.

**How we tested:** every source was run live on five companies before anything was built on top of it
(`backend/validation_report.md`). Prices were cross-checked against a second source; the last close matched within
0.13%.

### Step 4: The first real obstacle, and the decision it forced
The BSE and NSE announcement APIs refused automated access (HTTP 403). One retry with normal browser headers was
blocked by my own PC's safety check as an attempt to get around bot protection.

**My call:** we respect it and never try again. **The fallback we designed instead:**
- the exchanges' official RSS feeds (published for programs to read), polled every 5 minutes into a local database;
- plus Screener's list of recent filings;
- every brief says which sources worked for each company, so nothing is silently missing.

This one decision shaped the whole filings pipeline, and it is the reason FINN can say "primary sources only"
honestly.

### Step 5: Small things that turned out to matter
- A quarter is matched to the year-ago quarter by its end date, not by counting columns (a missing column broke the
  first version).
- Growth % is not shown when the base is zero or negative ("+250% profit" from a loss misleads).
- Banks and NBFCs are detected from their own table rows (NPA, financing profit), not from a list of names, so it
  works for any lender.

---

## Part 3 · The brief: filter → rank → verify

### Step 6: Teach FINN what a filing *is*
We hand-labelled **90 real filings** from the 18 holdings into ENAM's 17 categories. Ordered rules sort most of
them; Gemini Flash-Lite reads page 1 only when no rule is sure.

**Results:** 100% correct category on the labelled set. On a blind set of 34 *other* companies: 53% with rules
alone, **82% with rules + AI**, for only 15 AI calls. Most filings never touch the AI at all.

### Step 7: Rank by how much it should interrupt you
Every filing gets a score: category × the event's details (a CEO quitting is not a company secretary quitting)
× how big the holding is × your preferences + a bonus if the stock moved unusually. Cards above 0.6, one-liners
above 0.3, everything else collapsed (never deleted).

**Why it matters:** the app can answer "why am I seeing this?" with every factor. That became the **Why?** button
on every card.

### Step 8: Results cards: the AI reads, Python checks
For quarterly results, the AI reads only the results-table pages. Python then checks:
three periods line up, profit before tax − tax = profit after tax, totals add up, units are right, and the numbers
match a second source. Only then does a card say **Verified**.

**What testing caught (each became a general rule, not a one-off fix):**
- ITC's revenue included excise duty → excise is netted out.
- Small companies report half-yearly, not quarterly → handled.
- Scanned PDFs with no text → the AI reads the page images.
- Columns printed out of order → detected and re-ordered.
- An AI summary quoted *standalone* profit while the card showed *consolidated* → headlines are now written by
  Python from the verified numbers.
- An AI summary said "ICRA upgrades" when the filing said "reaffirmed; outlook positive" → action words must appear
  in the filing itself.

### Step 9: Price alerts that are not noise
A 3% day is noise for a small company and huge for a utility. So FINN measures each day against **the stock's own
usual daily move, after taking out the market's move**, plus volume vs its 20-day average.

**How we chose the default:** a 90-day backtest across 18 stocks. The obvious rule (2.5× the usual move) would have
pinged ~3 times a week. The chosen default (3× the usual move *and* 2.5× volume) pings ~once a week. Filings just
before a move are shown as "filed before", never "caused", because timing is a fact and cause is not.

---

## Part 4 · Research: does management keep its word?

### Step 10: The promise ledger
For any company: read the last five earnings calls → pull out every target management set → resolve the deadline
(Indian financial years, "H2", "next year") → measure it against what was later reported → verdict, with the exact
quote, speaker and page.

### Step 11: I made it prove itself by hand
We hand-checked 45 statements from L&T and HAL:
- extraction: **45/45** genuine and quoted word for word;
- verdicts: **only 4 of 7 right on the first pass.**

**What was missing:** L&T's 8.5% margin guidance was for its core engineering business, not the whole group, so
comparing it with the group's margin wrongly said "Kept". **Fix:** every promise now carries a *scope*, and only
company-wide targets are judged against company-wide numbers. After this and two other general fixes: **8/8.**

Other honesty rules that came out of testing:
- Guidance in constant currency or US dollars (IT companies) is marked "not measurable" instead of converted.
- "Quietly dropped" needs **two** later calls with no mention at all; one quiet call is not enough to accuse.

### Step 12: Did they answer the question?
A judge reads each analyst question and answer. The first version flagged a *clarification* as a dodge, so we made
it strict: Python keeps "dodged" only when the quoted answer itself shows the refusal. Every "dodged" flag on CDSL
was later read by hand: all four are explicit refusals ("that's a forward-looking statement, so we will not be able
to comment").

### Step 13: Analysis written by Python, phrased by AI
- **FINN's take:** one line at the top of each company, e.g. "Kept 3 of 6 promises · growth slowing 29% → 10% ·
  margins widening". Built by Python from verified facts.
- **Bull vs bear:** Python computes comparison facts first (growth slowing vs its 3-year trend, profit growing slower
  than revenue, a merger-sized jump confirmed by per-share dilution); the AI only phrases bullets from numbered facts,
  and any bullet whose numbers don't match its facts is thrown away. This is how FINN noticed that HDFC Bank's
  3-year growth includes its merger, without falsely accusing a fast organic grower like Dixon.
- **Ask about this company:** answers only from the company's cited evidence; Python re-checks every number; if the
  sources don't cover it, it says so.
- **Bank numbers:** for lenders, net interest income, an approximate margin, bad-loan ratios where reported and
  deposits. What the statements don't contain (CASA, credit-deposit ratio) is listed as missing, not guessed.

---

## Part 5 · The app: making trust feel effortless

### Step 14: Build it as a phone app
React + Vite, installable on a phone (PWA). It ships with a snapshot of real outputs so the link always works,
and calls a live research engine for any company outside it.

**How every change was tested:** every screen was screenshotted at phone size and checked automatically for
console errors, accessibility, colour contrast and layout overflow. By the end: **20 screens, 0 errors, 0
accessibility problems**, re-checked after almost every change.

### Step 15: I reviewed on my phone and pushed back, a lot
This is where most of the polish came from. A few examples of how I steered it:
- "The first page looks clumsy, who wants to wake up to this?" → the header was simplified to one calm line.
- "I want the first page as clean and pretty as before" → the original look came back, with the new content kept.
- "The neon green looks tacky; apps usually have a plain background" → a calmer sage-mint and a plain near-black
  background, with a tint only near the logo.
- "The font is too big, it doesn't look premium" → one step smaller, numbers in a cleaner font.
- "Things clash here" → the research list, the alert sentence and the backtest rows were re-laid out.
- "It's very hard to navigate" → labels on every tab, a sticky jump bar on company pages, a back link, smooth
  transitions.
- "The bottom bar is bulky… now it's lost in the page" → slimmer, then given a raised 3D look.
- "The voice that reads the news sounds mechanical and over-engineered" → removed.
- "Mute and Normal look the same" → each choice got its own colour; "too bouncy… just a little bounce" → tuned.

### Step 16: My identity for FINN
I designed the logo, the slanted F, and asked for a lighter, wider-spaced wordmark. When the app opens, the F
assembles itself in a short animation. When it flickered on iPhone, we found the real cause (an animated layer
over blurred panels, plus a font swap) and rebuilt it so the animation plays alone and the app fades in after.

### Step 17: Visuals that explain, not decorate
- A filter funnel in the header: "20 filings → 3 worth knowing → 1 need you".
- A portfolio pulse: how many holdings beat the Nifty this week, and the biggest move.
- Results cards show "your 6% holding", a Verified badge you can open, Why? and Done.
- Bar charts with older years in grey and the latest two highlighted, tap-to-read values, and one Python sentence
  above each chart.
- Alert days drawn as glowing peaks, taller for bigger moves.
- Cash quality as a green mountain of cash earned per ₹1 of profit against a dashed ₹1 line.

### Step 18: An outside review, used properly
I brought in a detailed critical review of the app. Instead of applying everything, we triaged it against the
challenge brief: what a reviewer sees in the first minute, what the brief explicitly asks for, and what was too
risky on submission day. The first screen was never to be empty again, verified results got pinned, copy was
cleaned up (₹, dates, no developer words), the API was protected, and the bull/bear facts got smarter.
One item, checking vague "margins should improve" statements, was **deliberately left out**: doing it properly would
have meant re-reading every call and adding verdicts nobody had hand-checked on the last night. A wrong "Missed" is
worse than an empty one.

---

## Part 6 · Shipping it like a real product

### Step 19: Deploy
- **App:** Vercel. **Research engine:** Render (free plan).
- When Render asked for a card, I chose to stay on Render and set it up myself; the AI then tested the live server
  end to end: health, a known company, a brand-new company read live in about 5 minutes, and the Ask box.
- When Vercel was first deployed without its setting, we fixed it in one redeploy.

### Step 20: Fallbacks, because free servers sleep and sources fail
- **The app always works:** a built-in snapshot of real outputs; the live server is used for new companies.
- **Sleeping server:** the app waits and says "waking up the free server" instead of failing.
- **Busy server:** one company is read at a time, and the app shows "1 ahead of you · about 4 min".
- **Fresh data without my laptop:** a daily GitHub Action rebuilds the data. I ran it once by hand to prove it works
  from GitHub's servers. If one company's fetch fails, that company keeps its previous data.
- **Protecting the free AI quota:** only the app itself can call the server, and each visitor is rate-limited.
- **Fresh server, no memory:** a small committed "seed" of cached answers, so a restart doesn't re-pay for work.
- **Cost numbers can't shrink:** a fresh cloud run no longer resets the build's AI totals.

### Step 21: What was missing, found by testing
- The first screen showed "0 filings" on a quiet day → it now shows what mattered this week.
- The cost meter claimed "today" for build totals → corrected, then moved to a quiet section at the bottom.
- The automated screenshot run had silently stopped halfway after a new button was added → found, fixed, and every
  check re-run from scratch.
- The phone couldn't reach the laptop on campus Wi-Fi → solved for good by the public Vercel link.

---

## Part 7 · How the AI was used, in numbers

- **Claude Code** did the engineering: planning, code, live runs, tests, screenshots, accessibility checks, git
  commits and deployment checks, and reported back in plain language after every step.
- **Gemini** inside the app: one router with fast and stronger tiers and automatic fallback; every answer cached by
  a hash of its exact input; every call logged and costed.
- **Whole build:** about 400 model calls and 1 million tokens, two-thirds of requests answered from cache:
  **USD 0** on the free tier.
- **Proof, not claims:** 119 offline tests, hand spot-checks of promises and dodged questions, a 90-day alert
  backtest, and 20 screens checked after almost every change.

## What the AI got wrong, and how we caught it

| Mistake | Caught by | Fix |
|---|---|---|
| Judged L&T's segment margin target against group margins | hand spot-check | every promise has a scope |
| "ICRA upgrades" for a reaffirmed rating | summary checks | action words must appear in the filing |
| Treated a CEO as a page header, a CFO as an analyst | live runs | roles from introductions and Q&A behaviour |
| Flagged a clarification as a dodged question | hand check | stricter judge + Python evidence rule |
| Listed "0 questions dodged" as a bull point | review | Python comparison facts, each tied to a side |
| Built a hosting alternative I hadn't asked for | me | removed; options are offered, not built |
| Reported "0 errors" from a stale test run | the AI itself | test fixed, all checks re-run, correction sent |

Every step above is in the git history (`git log`), one commit per change.
