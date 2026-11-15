# How FINN was built: a working log

FINN was built in about two days (13–15 November 2026) by the author working with **Claude Code** (an AI coding
agent) on a Windows PC, steered from a Claude project conversation. The author set the direction, made the product
calls and reviewed the app on a phone; Claude Code wrote the code, ran it against live sources, tested it and wrote
up what it found. Gemini (free tier) is the model *inside* the app. Every step was committed to git: 37 commits,
listed at the end.

This log is a readable account of that collaboration. The raw conversation exports sit next to it (see
`README.md` in this folder).

## How we worked

- **One plan, six tasks.** Setup → data pipes → push engine → pull engine → app → submission (`PLAN.md`). Each
  task ended with something running on live data and a report the author could read (`backend/*_report.md`).
- **Rules written down first.** `CLAUDE.md` fixed the non-negotiables before any code: primary sources only, no
  bot-protection workarounds, the model reads and Python decides, quotes checked word for word, never commit
  secrets. When a rule cost something, the cost went into `DECISIONS.md`.
- **The author asked for quality over speed** ("I want a great app that can actually stand out"), and for
  plain-language updates. Claude reported in that style and kept a progress checklist.
- **Prior art.** The author asked Claude to keep looking for people who had built similar things better. That led
  to the materiality score with a visible "why", the backtest-first alert rule, and the promise-ledger framing.

## Phases and turning points

### 1. Setup and data (13–14 Nov)
- Earlier code from a previous attempt (well designed, never run live, written for another model provider) was
  kept for reference, and the data layer was rewritten and **proven live** on five companies
  (`backend/validation_report.md`).
- **BSE's and NSE's announcement APIs refused scripted access (403).** One retry with standard headers was blocked
  by the PC's own safety check as bot-check circumvention. Decision: respect it, never retry, and use the exchanges'
  official RSS feeds plus Screener instead. This shaped the whole filings pipeline.

### 2. Push engine (14 Nov)
- 90 real filings were hand-labelled into ENAM's 17 categories. Rules first, Gemini Flash-Lite only when no rule is
  sure: 100% category on the labelled set; on a blind set of 34 other companies, 53% (rules) → 82% (rules + model).
- **Live runs caught model mistakes**, and each became a generic check rather than a special case:
  "ICRA upgrades" when the filing said "reaffirmed; outlook positive" (action words must be the filing's);
  an LLM summary quoting standalone profit while the card showed consolidated (headlines now written by Python);
  ITC revenue including excise duty (netted out).
- **The alert default came from a backtest**, not a guess: the obvious 2.5-sigma rule fired ~3 times a week across
  18 stocks; "3 sigma and 2.5× volume" fires about once.

### 3. Pull engine (14 Nov)
- Transcripts, a promise ledger, a dodged-question judge, segments from the annual report, bull/bear.
- **Hand spot-check of 45 statements** (`backend/spot_check.md`): extraction 45/45; verdicts were **4/7 on the first
  pass** — the hand check found L&T's 8.5% margin guidance was for its core business, not the group. Fix: every
  promise carries a scope, and only company-wide targets are judged against company-wide tables. Verdicts 8/8 after.
- The dodged judge first flagged a clarification request as a dodge; it was made stricter (Python keeps "dodged"
  only with evidence in the quoted answer).

### 4. The app (14 Nov)
- React + Vite PWA, checked on every screen with Playwright and axe (accessibility, contrast, overflow).
- Ships a snapshot of real outputs so the link always works; a live backend reads companies outside it.
- Added late on 14 Nov: **Ask about this company** (answers only from cited evidence, numbers re-checked) and
  **Play my brief** (the phone reads the cards that matter).

### 5. Deployment (14–15 Nov)
- Render (backend) asked the author's account for a card. Claude prepared a no-card alternative without being asked;
  **the author chose Render and asked for the alternative to be removed** — it was, and Claude now offers options
  and waits for the choice. The author set up Render, Vercel and the GitHub secrets; Claude tested the live backend
  end to end (health, a cached company, an unseen company read live in ~5 min, Ask).
- Campus Wi-Fi kept the phone from reaching the laptop, so the author moved straight to the public Vercel link.

### 6. Review and polish (15 Nov)
- The author brought in an outside review (scores per area, a ranked list of issues). Claude triaged it against
  the challenge brief and did the deadline-safe items:
  - the first screen is never empty (a quiet window shows the shortest window with something, labelled);
  - verified results are pinned under "Latest results";
  - Python comparison facts for bull/bear: growth slowing vs trend, margins squeezed, and a **merger-sized year
    confirmed by per-share dilution** (HDFC Bank's 3-year growth includes its merger; Dixon's fast organic growth is
    not flagged);
  - mute / normal / boost per announcement type; % equivalent on the alert slider;
  - CORS limited to the app and per-visitor rate limits, so the shared free AI quota can't be drained;
  - the 4 CDSL "dodged" flags and Reliance's +11.6% day were checked by hand (all genuine).
- **Design went back and forth, and the author decided.** Claude toned down the colour and glow per the review; the
  author preferred the original look and asked for it back, with the new content kept. The author also supplied the
  final logo (the slanted F) and asked for a lighter wordmark, clearer navigation and smoother motion.

## What the AI got wrong, and how it was caught
| Mistake | Caught by | Fix |
|---|---|---|
| Treated a frequent speaker as a page header (Infosys CEO), a CFO as an analyst (HDFC Bank) | live run | speaker roles from moderator introductions and Q&A behaviour |
| Judged L&T's segment margin guidance against group margins ("Kept") | hand spot-check | promise scope |
| "ICRA upgrades" for a reaffirmed rating | summary checks | action words must appear in the filing |
| Flagged a clarification request as a dodged question | hand check | stricter judge + Python evidence rule |
| Bull points like "0 questions dodged" and growth numbers listed as bear points | outside review | comparison facts with a side; model may not move a fact to the other side |
| A test that reached the live model once a working key was present | test run | tests forced offline |
| Built an unrequested hosting alternative | the author | removed; options are offered, not built |

## Numbers at the end
- 115 backend tests; 20 app screens checked with 0 console errors and 0 accessibility issues.
- Model use for the whole build: about 330 Gemini calls and 1 million tokens, two thirds of requests answered from
  cache, **USD 0** (free tier).

## Commit history
`git log --reverse --oneline` shows all 37 commits in order, from "Task 1: project setup" to the final design
fixes on 15 November.
