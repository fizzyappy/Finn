# How FINN was built

FINN was designed and directed by the author and built with **Claude Code** as the engineering agent. The
author set the product direction, made every product and design call, reviewed each build on a phone, and
**designed FINN's logo (the slanted "F")** personally. Claude Code wrote the code, ran it against live data,
tested it and reported back. Gemini (free tier) is the model *inside* the app, used only where rules can't do
the job.

The aim was not "an app that calls an LLM". It was an app an investor could trust: every number traceable to
a filing, every quote checkable, and the AI used only where it earns its place.

---

## 1. Research first: what should this app be?

**Method.** Before writing code, we read the challenge as an investor would, and asked: what does someone with
18 stocks actually need on a Tuesday morning? Three answers drove everything:

- **Most filings are noise.** Indian listed companies file dozens of announcements a week, nearly all paperwork.
  The value is in *filtering*, not summarising everything.
- **Trust is the product.** A wrong number in a finance app is worse than no number. So the model may *read*,
  but Python must *decide*.
- **Management credibility is under-served.** Everyone shows results; almost nobody checks whether management
  did what it said on the last five calls. That became the signature feature: the **promise ledger**.

**Design thinking.** We worked from first principles on what makes an investor trust a screen: show why each
item is there, test every alert rule on history before switching it on, and tie every verdict to a quote and
page. These became FINN's visible "Why?", its alert backtest and its promise ledger.

**First-principles rules, written down before code** (`CLAUDE.md`, `DECISIONS.md`):
1. Primary sources only (exchange filings, transcripts, annual reports), and no bot-protection workarounds.
2. Rules before models; the model reads, Python does all arithmetic and every verdict.
3. Quotes must be found word for word in the source, or they are dropped.
4. Every model call is cached and costed.

---

## 2. Data pipes: proving the sources live

**What.** A data layer for any NSE company: prices, statements, transcripts, filings and documents.
**How.** Each source was tested live on five companies before anything was built on it
(`backend/validation_report.md`). When the BSE/NSE announcement APIs refused scripted access, we did not
work around it: we switched to the exchanges' official RSS feeds plus Screener, and documented the trade-off.
**Why it matters.** Every later feature stands on numbers we had already checked against a second source
(last close within 0.13%).

---

## 3. Push engine: filter → rank → verify

**Filter.** 90 real filings were hand-labelled into ENAM's 17 categories. Ordered rules handle most; Gemini
Flash-Lite reads page 1 only when no rule is sure. Result: 100% category on the labelled set; on a blind set of
34 other companies, 53% with rules alone → 82% with rules + model.

**Rank.** A materiality score (category × event details × holding weight × the user's preferences + market
reaction), with every factor shown under **Why?**. Thresholds: card ≥ 0.6, one-liner ≥ 0.3.

**Verify.** Results numbers are read from only the results-table pages; Python then checks three periods, PBT −
tax = PAT, totals, units and a match with Screener before a "verified" badge. Live runs caught real issues
(ITC revenue including excise, half-year reporters, scanned PDFs), and each became a general rule.

**Alerts.** Price moves are judged against each stock's own usual daily move after the market's move, plus
volume. The default came from a 90-day backtest: the obvious rule fired ~3×/week; the chosen one ~1×/week.

---

## 4. Pull engine: does management keep its word?

**What.** For any company: last five transcripts → every target management set → measured against what was
later reported → a verdict with the exact quote and page. Plus a dodged-question check, business segments from
the annual report, a bull/bear case and an **Ask** box that answers only from cited evidence.

**How we kept it honest.** A hand spot-check of 45 statements: extraction 45/45; verdicts 4/7 on the first
pass. The miss was instructive: L&T's margin guidance was for its core business, not the group. Fix: every
promise carries a scope, and only company-wide targets are judged on company-wide tables (→ 8/8).

**Python-written analysis.** "FINN's take" (one line per company), the bull/bear facts (growth slowing vs its
trend, margins squeezed, a merger-sized year confirmed by per-share dilution) and the sentence above each chart
are all computed by Python; the model only phrases bullets from numbered facts, and bullets that don't match
their facts are dropped.

---

## 5. The app: making trust feel effortless

**Stack.** React + Vite PWA, installable on a phone, with a built-in snapshot of real outputs (so the link always
works) and a live backend for new companies.

**Design method.** Every screen was screenshotted at phone size and checked automatically for console errors,
accessibility, contrast and overflow after every change (20 screens, 0 issues at the end). The author reviewed
on a real phone and directed the look in short loops. Key design decisions:
- **Identity:** the author's own slanted-F logo, a calm dark theme with one sage-mint accent, and a short opening
  animation in which the F assembles itself.
- **First screen never empty:** a quiet day says "Today: nothing new" and shows what mattered this week, with a
  filter funnel ("20 filings → 3 worth knowing → 1 need you") and a portfolio pulse vs the Nifty.
- **Every card answers "so what?":** your holding size, a verified badge you can open, Why?, Done, and company
  names that open their research.
- **Visuals that explain, not decorate:** bar charts with the latest years highlighted, tap-to-read values, a
  Python sentence above each chart, glowing "peak" bars for alert days, and a mountain chart for cash earned per
  ₹1 of profit against a dashed ₹1 line.
- **Settings that feel like a phone:** Mute / Normal / Boost per announcement type on a sliding toggle.

---

## 6. Shipping it like a product

- **Hosting:** Vercel (app) + Render (research engine), with CORS limited to the app and per-visitor rate limits
  so the shared free AI quota can't be drained.
- **Fresh data without a laptop:** a daily GitHub Action rebuilds the data; if one company's fetch fails, its
  previous data is kept.
- **Cold starts handled:** a committed seed of cached answers, a waking-up message, and a queue position
  ("1 ahead of you · about 4 min").

---

## 7. Using AI efficiently

- **Claude Code as the engineer:** planned in tasks, wrote code, ran it on live sources, tested and reported in
  plain language; the author steered priorities and design.
- **Gemini only where it earns its place:** one router with tiers and fallback, every answer cached by a hash of
  its input, every call logged. Whole build: ~400 model calls, ~1 million tokens, about two-thirds served from
  cache, **USD 0**.
- **Verification over trust:** 119 offline tests, hand spot-checks, a backtest for alerts, and an outside design
  review that was triaged against the brief before acting on it.

## What the AI got wrong, and how it was caught

| Mistake | Caught by | Fix |
|---|---|---|
| Judged L&T's segment margin guidance against group margins | hand spot-check | promise scope |
| "ICRA upgrades" for a reaffirmed rating | summary checks | action words must appear in the filing |
| Treated a CEO as a page header, a CFO as an analyst | live runs | roles from introductions and Q&A behaviour |
| Flagged a clarification as a dodged question | hand check | stricter judge + Python evidence rule |
| Bull points like "0 questions dodged" | outside review | Python comparison facts, each tied to a side |
| Built an unrequested hosting alternative | the author | removed; options are offered, not built |

The full commit history (`git log`) shows every step.
