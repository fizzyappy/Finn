# Part 1 · Research, analysis and the plan

This series explains how FINN was built: the thinking behind each decision, how I worked with AI to execute it,
what testing showed was missing, and how we closed each gap. FINN's logo, the slanted "F", is my own design.

- Part 1 · Research, analysis and the plan (this file)
- [Part 2 · Data pipes and the push brief](02-data-and-brief.md)
- [Part 3 · The research engine](03-research-engine.md)
- [Part 4 · App design and user experience](04-design-and-ux.md)
- [Part 5 · Deployment, fallbacks and final polish](05-deploy-and-polish.md)

---

## 1.1 Where this started: our own analysis and prototype

FINN did not start from a blank page. Before this build, I had already done the problem analysis in earlier
working sessions with AI and turned it into a hypothetical prototype: a written analysis of the challenge, a
category taxonomy for exchange filings, a scoring idea for ranking them, and first versions of a classifier, a
push digest and a research engine.

That prototype was the starting asset, and it was also the first thing I asked the AI to judge honestly. The
review found three things:

- **The thinking held up.** The taxonomy idea (ordered rules, sub-types, base scores per category), the ranking
  logic and the research concept were sound, and became the backbone of FINN.
- **It had never touched real data.** The code had been written but never run against live sources, so none of
  its assumptions about the data were proven.
- **It was built for a different model provider.** The model layer had to be rebuilt around the one we would
  actually use.

So the build plan was not "start over", and not "ship the prototype". It was: keep the analysis, prove every
assumption against live data, and rebuild whatever did not survive that test. The old code was kept aside as a
reference, and every module in FINN was rewritten and tested against real filings.

## 1.2 Reading the brief like an investor

My first instruction set the bar for the whole project: this was not to be a quick app, it had to be a great
one, good enough to stand out against submissions from the strongest candidates. That changed how every later
decision was made. Speed was never the goal; trust and quality were.

The analysis of the brief started from the user, not the technology. Who is the user? Someone holding 15 to 20
Indian listed stocks who does not have time to read exchange filings. What actually happens to that person?

- **The problem is volume, not access.** Listed companies file dozens of announcements a week: board meeting
  intimations, trading window closures, newspaper publication notices, investor meeting schedules. Almost all of
  it is paperwork. The useful filings (results, a CEO leaving, a large order, a fund raise, a rating change) are
  buried in the noise.
- **Therefore the product is the filter.** Summarising everything would just create a shorter pile of noise.
  FINN's job is to decide what deserves attention and to explain why.
- **The second unmet need is credibility.** Every app shows results. Almost none answers the question an
  experienced investor actually asks: did management do what it said it would? Earnings-call transcripts are full
  of targets, and nobody systematically checks them against the next year's numbers. That became the
  signature feature: the **promise ledger**.
- **Trust is the product.** In a finance app, one wrong number destroys the credibility of every other number.
  So the design question was never "how do we use AI everywhere?" but "where can AI be trusted, and how do we
  prove it?"

## 1.3 The rules, set before any code

From that analysis came a small set of rules. They were written into `CLAUDE.md` (the AI's standing
instructions for the project) and `DECISIONS.md` (the log of every trade-off), and every later decision was
checked against them.

1. **Primary sources only.** Exchange filings, earnings-call transcripts and annual reports. No third-party
   news, no social media, no scraped opinions.
2. **Rules first, AI second.** If a rule can do it, a rule does it. The AI is used only where language
   understanding is genuinely needed.
3. **The AI reads; Python decides.** The model may read a document and phrase a sentence. Every calculation,
   every comparison and every verdict is done in Python, where it can be tested.
4. **Quotes must be real.** A quote is shown only if it is found word for word on the page it cites.
5. **Every AI call is cached and costed.** The same input is never paid for twice, and the total cost is always
   known.
6. **No workarounds for bot protection.** If a website refuses automated access, we respect it and find a
   legitimate source.

Two more rules governed how I worked with the AI itself:

- **The AI does the work, end to end.** I asked Claude Code to work in my project folder directly: write the
  code, run it, test it, fix it, and report back. I did not want to copy and paste code between windows.
- **Plain-language reporting.** I am not a deployment engineer, so every update had to say, in plain words, what
  was done, what changed, what was tested, and exactly what I needed to do next. Anything that touched an account,
  a password, a payment or a public repository was left for me to do, with step-by-step instructions.
- **Ask before anything irreversible.** Installs, account creation, commits and pushes needed my go-ahead until I
  explicitly asked the AI to work autonomously in the project folder and push after each step.
- **Keys never leave my machine.** The Gemini API key lived only in a local `.env` file, was never echoed, never
  logged and never committed, and every commit was scanned for it before it went out.

## 1.4 Choosing the tools

**Claude Code as the engineer.** I used Claude Code running on my Windows PC, inside the project folder, as the
engineering agent. It planned in tasks, wrote and ran code, ran tests and headless browser checks, made git
commits and pushed to GitHub. I steered priorities and product decisions, reviewed every version on my phone,
and directed the design.

**Gemini inside the app.** The app's own AI needed to be cheap, fast and good at reading documents. We tested the
available Gemini models live with my key before choosing: two tiers, a fast low-cost model for bulk reading
(classifying filings, extracting targets, phrasing bullets) and a stronger model for harder tasks, behind a single
router with automatic fallback. Models that did not answer reliably on a new free key were not used. Everything
runs on the free tier.

**A stack chosen for reliability, not novelty.**

- Backend: Python with FastAPI, SQLite as a cache (stored as JSON, never pickled, so it is safe to load and
  readable by eye).
- Frontend: React with Vite and TypeScript, built as an installable phone app (a PWA).
- Verification: an automated headless browser that screenshots every screen and checks accessibility, contrast
  and layout after each change.
- Hosting: free tiers only (Vercel for the app, Render for the research engine, GitHub Actions for daily data
  refreshes).

## 1.5 The plan: six tasks, each ending in proof

The AI broke the challenge into six tasks, and I approved them with one condition: every task had to end with
something running on live data and a written report I could check.

| Task | What it delivers | Proof at the end |
|---|---|---|
| 1. Setup | Project folder, rules, tool check | A clean repository and a verified toolchain |
| 2. Data pipes | Prices, statements, transcripts, filings for any NSE company | A live validation report on five companies |
| 3. Push engine | Classify, rank, verify, alert | A live run report and backtests |
| 4. Pull engine | Promise ledger, dodged questions, analysis | A research report on real companies and a hand spot-check |
| 5. App | The phone app | Screenshots and automated checks of every screen |
| 6. Submission | README, decisions, demo path, build history | Documents that match the final app |

A few planning decisions shaped everything that followed:

- **Prove the data first.** Nothing would be built on a source until that source had been tested live.
- **Ship a snapshot inside the app.** A deployed prototype on a free server can be asleep, or a source can refuse
  a request on the day a reviewer opens the link. So the app ships with a snapshot of real outputs and only calls
  the live server for companies outside it. The link must always work.
- **Log every trade-off.** Every time we gave something up, the reason went into `DECISIONS.md`. That log grew to
  more than sixty entries and became part of the submission.

## 1.6 The project folder decision

One small decision at the very start avoided a lot of pain later. The project was placed in a plain local folder
rather than a cloud-synced one, because sync services fight with dependency folders, virtual environments and
database files. GitHub became the backup instead. It is the kind of decision that never shows in the final app,
but it prevented a whole class of mysterious failures during the build.

## 1.7 Constant critique

Throughout the build I asked the AI to keep analysing its own work: to keep looking for weak spots, to compare
each part with how a stronger version would be built, and to tell me plainly when something was not good enough.
That instruction is why the build history is full of "testing showed this was missing" moments: the AI was
expected to find its own mistakes before a reviewer did, and to fix them with general rules rather than special
cases.

---

Next: [Part 2 · Data pipes and the push brief](02-data-and-brief.md)
