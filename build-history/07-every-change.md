# Every change, in order

[← Part 5](05-deploy-and-polish.md) · [Back to Part 1](01-research-and-plan.md)

This is the complete list of changes made while building FINN, in the order they happened, taken from the
project's commit history. Each entry is one change that Claude Code made, tested and pushed, most of them because
I asked for them after reviewing the app on my phone. Where a design went back and forth, every step is here,
including the versions I rejected and why.

---

### 1. Task 1: project setup - rules, plan, decisions log, ignore rules

### 2. Task 2: data layer for any listed company (backend/finn)

Prices (yfinance + Yahoo chart fallback, provisional late bar, quality checks),
company resolution from NSE's company list, screener.in statements and document
links, headline results with Python-only arithmetic and date-matched YoY,
filings merged from four sources with per-source status, RSS poller, PDF
download and page text with quote verification, SQLite JSON cache with
stale-on-error, polite HTTP that backs off when a site refuses, FastAPI app.

### 3. Task 2: offline tests on real captured responses (34 tests)

### 4. Task 2: live validation report, decisions log, plan status

### 5. LLM router: Gemini tiers with fallback, content-hash cache, token log

One module for every model call: lite/flash tiers with fallback chains
(labelled), retries with backoff on rate limits and server errors, pacing
for the free tier, a SQLite cache keyed by a hash of the exact input
(prompt, schema, attached PDF), and a per-call log that feeds the cost meter.
Offline or without a key it returns None and callers fall back to rules.

### 6. Task 3: push engine (classify, score, cards, alerts, digest)

- 17-category classifier: ordered rules first, Gemini Flash-Lite reads
  page 1 only for filings no rule recognises
- materiality score with every factor returned ("why am I seeing this"),
  hero / one-liner / collapsed treatment
- results card: results-table pages sent as a mini PDF; Python checks
  periods, PBT - tax = PAT, totals, units and screener before "verified";
  handles excise duty, half-yearly reporters, scanned filings, odd columns
- people card: profile lines verified word for word with page numbers
- summaries: numbers, praise words and action verbs checked against the
  filing; templates for ratings and dividends
- end-of-day alerts vs each stock's own normal (beta to Nifty, sigma),
  presets and custom rules, 90-day backtest, "filed before" linking
- digest builder -> brief.json for 24h / 3d / 7d / since last look / custom

### 7. Task 3: tests on 124 hand-labelled real filings and recorded model answers

81 offline tests in total (47 new): classifier accuracy on 90 portfolio
filings and 34 other-company filings, materiality factors, results-card
checks on recorded Gemini readings (ITC, half-yearly SME, out-of-order
columns), people-quote verification, summary guards, alert maths and
backtest, digest helpers, and the LLM router with a fake client.

### 8. Task 3: live run report, sample briefs, backtests, decisions log

### 9. Stricter default alert: notable move (3 sigma and 2.5x volume)

The 90-day backtest showed a plain 2.5-sigma rule fires ~3 times a week
across 18 holdings; requiring a 3-sigma move after the market on at least
2.5x normal volume brings it to ~1.2 a week. Other presets stay available.
Results cards now carry open management targets ("vs guidance") when the
company has been researched.

### 10. Task 4: pull engine (research on demand from primary sources)

- table sections with no LLM: snapshot, multi-year trajectory, balance
  sheet (debt, D/E, working capital), cash quality; lender schema
- transcripts: speakers and roles found from each document (moderator
  introductions, participant list, behaviour), Q&A pairs
- promise ledger: rules pick management's forward-looking sentences,
  Gemini Flash-Lite extracts strict JSON, every quote verified on its page;
  revision trails (set, raised, cut, held, pushed out, quietly dropped);
  actuals and verdicts computed in Python from the tables, with scope,
  constant-currency and far-off-target guards; management's own
  explanation quoted when found
- dodged questions: answered / partly / dodged with both quotes verified
- business snapshot: segment mix from the annual report, checked against
  reported revenue
- narrative vs numbers (no LLM) and bull vs bear (cited facts only)
- report card, research job with stages and cache, API endpoints
- quote checks ignore PDF spacing but nothing else

### 11. Task 4: live research on six companies, hand spot-check, decisions

Research reports for INFY, LT, HDFCBANK, ASIANPAINT, TITAN and HAL; hand
spot-check of 45 L&T and HAL statements (45 of 45 genuine, verbatim;
first-pass verdicts 4 of 7 right, 8 of 8 after the generic fixes);
refreshed push report with the new default alert rule; 110 offline tests.

### 12. Task 5: the FINN app (React + Vite + TypeScript PWA)

- Brief: progress ring, window chips that re-rank instantly, swipeable hero
  cards (right = clear, left = less like this, bounded), flip to the score
  breakdown, results card with count-up numbers, verified badge and checks,
  vs-guidance line, people card with sourced career lines, one-liners,
  unusual moves, collapsed categories, quiet-day and "You're clear" states,
  read aloud
- Research: search with autocomplete over NSE's company list, report card,
  promise ledger with verbatim quotes, page links, revision trail and
  target-vs-actual chart, dodged questions, story vs numbers, tables and
  charts, segments, bull vs bear, sources; cold start with staged progress
  from the job API, honest states
- Alerts: rule as a sentence, sliders, live 90-day backtest strip
- Settings: cost meter, portfolio, data status, backend URL, how FINN thinks
- Frozen snapshot of real outputs (export_snapshot.py); live backend used
  when reachable; service worker, manifest, icons, safe areas, reduced motion
- Screenshot + axe + PWA verification script (playwright-core, installed Chrome)
- Deployment config for Vercel and Render (not deployed) and DEPLOY.md
- Backend: slow-PDF guard and a time budget for annual reports

### 13. Task 5: final snapshot (21 companies), screenshots, polish

- research for all 18 holdings plus ASIANPAINT, TITAN, HAL in the app snapshot
- 18 phone-size screenshots of every screen and state (2x), 0 console
  errors, 0 accessibility / contrast / overflow issues, service worker active
- app finds the local backend automatically on this PC ("off" keeps it offline)
- plural fixes, plain-language data note
- backend: HTTP retries no longer wait on long Retry-After replies
- plan and decisions log updated

### 14. Live backend for the deployed app (Render free plan) with wake-up state

- render.yaml: free plan, Python 3.12, cloud requirements with lower bounds
- seed (285 KB): cached model answers and finished research, loaded at
  startup so a fresh server does not redo paid or slow work
- API: /sources shows which data sources this server can reach; root info
- app: backend URL from VITE_API_BASE (Settings value wins, local backend
  on this PC); "Waking up the research engine (up to 50 s)" state for a
  sleeping free server; clear messages when a source refuses or a ticker
  is unknown
- keep-warm GitHub Action pings /health every 10 minutes when the
  FINN_API_URL repository variable is set

### 15. Daily data refresh on GitHub Actions (no PC needed)

Every weekday at 16:45 IST, and on demand: load the seed and the last run's
database, rebuild the app's data snapshot (briefs, alerts, meta), refresh
the seed, and commit only if something changed; Vercel redeploys on the
push. Research re-runs only when asked. The export now refuses to replace
good data with a broken run (filings or prices failing for most holdings).
Needs the GEMINI_API_KEY repository secret.

### 16. Stricter dodged-question judge: fewer, evidenced flags

The model flags "dodged" only for clear non-answers; Python keeps the label
only when the quoted answer shows a refusal or deflection, or a number was
asked and the whole answer has none. Clarification requests are never
dodges. Re-run on the six demo companies: 2 dodged of 224 pairs, both
correct on a hand check (12 of 15 labels agree overall; spot_check.md).

### 17. Custom window: real date range picker

From/To dates with quick ranges (today, 5, 14, 30 days). Ranges inside the
built-in 14 days are filtered on the device instantly; older ranges are
fetched from the live backend's /brief when it is reachable, with a clear
note when it is not. Screenshot of the picker added (19 screens, 0 errors).

### 18. Results cards try other exchange filings; refreshed snapshot; deploy guide

- results card: up to 3 exchange-filed documents (the event's filing,
  filings folded into it, the company's other results filings in the
  window, results filings captured from the BSE/NSE RSS feeds); the first
  verified one wins; a results press release keeps its summary unless a
  verified table is found
- snapshot re-exported (stricter dodged labels, fallback cards), seed
  refreshed, 19 screenshots at 2x: 0 console errors, 0 a11y issues
- DEPLOY.md rewritten: Render first (required), Vercel with VITE_API_BASE,
  GitHub secret + variable for the daily refresh and keep-warm
- decisions log updated

### 19. Polish pass: plain labels, scorecards start page, clearer wording

- Research start page lists every ready company's management scorecard
  (promises kept, questions dodged), tap to open
- plain-English labels for metrics and filing types everywhere
- unusual moves in plain words; one-liners that repeat the headline hidden
- custom range title, "said Jun 2026" dates, score badge explained
- results card provenance in investor words; dodges listed first,
  clarification requests not shown as examples
- phone on the same Wi-Fi uses the PC's backend automatically

### 20. Ask about this company; Play my brief

- Ask: questions about a researched company are answered only from its
  evidence (computed facts, verified promise and call quotes, story vs
  numbers, segments). The answer must cite evidence ids; Python checks every
  number against the cited evidence and refuses invented numbers or praise
  without numbers; "not covered" when the sources don't answer it.
  POST /ask/{ticker}; Gemini Flash with Flash-Lite fallback, cached.
- Play my brief: hero cards only, about a minute (150 words), play/stop.
- tests for the Ask checks (113 passing)

### 21. Submission materials: README, demo script, email draft, build history

- README: pitch, screenshots, how FINN thinks (filter, rank, verify),
  architecture diagram, model routing with measured calls/tokens/cost,
  evaluation results with links, key decisions, what we left out, next
  steps, how to run locally
- DEMO.md: a 90-second path through the app
- SUBMISSION_EMAIL.md: draft covering email with placeholders (not sent)
- DECISIONS.md: preface with the decisions that shaped FINN most; no
  personal paths
- build-history/: the build phases and where each phase's evidence lives

### 22. Final data refresh, Ask screenshot shows a real answer, docs match the app

- Annual-report reader runs in a background thread with a 4-minute budget,
  so a slow report can no longer keep a finished run alive
- Re-checked all 21 companies; refreshed app data, research report and seed
- Ask screenshot waits for the cited answer (20 screens, 0 console errors,
  0 accessibility or overflow issues)
- README: 20 screens, Play my brief and Ask, final model use (~331 calls,
  ~1.02M tokens, USD 0); DEMO numbers match the current data; three new
  rows in DECISIONS

### 23. Hugging Face Space option for the backend (no card needed)

- hf-space/Dockerfile clones the public repo and runs the API on port 7860,
  data in /tmp, seed included
- DEPLOY.md: click-by-click Space steps, key stored as a Space secret

### 24. Backend: Render deployment config

Removes the unused Hugging Face backup; Render is the backend host.

### 25. Docs: live backend address

### 26. Settings: wait for the free server to wake before saying it is unreachable

### 27. Review pass: never-empty brief, calmer design, sharper bull/bear, API limits

Brief
- A quiet window falls forward to the shortest window that needs attention,
  labelled; first visit opens on 24 hours; latest verified results pinned
- No empty-state card next to "worth knowing" items; ring, Play and the
  collapsed header hide when there is nothing to show; one-time tip
- Rupee sign and Indian date style in card text; plain source line
Design
- Type one step smaller; numbers in Inter with tabular figures
- Mint kept for the primary action and data; selection is a raised neutral;
  glows removed; nav more opaque; bell icon for Alerts; no truncated badges
Research and Alerts
- Scorecards sorted by verdicts, with targets tracked, next due and last call
- Report card collapses to one line when nothing is due; Ask suggestions
  come from what the sources contain; price and market cap in the header
- Alert slider shows the % equivalent; verdict line follows the count
Analysis
- Python comparison facts for bull/bear: growth slowing vs trend, profit vs
  revenue, a merger-sized year confirmed by EPS dilution; each fact marked
  for its side, and "0 dodged" is no longer a bull point
- Bull/bear rebuilt for the 21 companies from cached sources
Backend
- CORS limited to the app's own address and local addresses; per-visitor
  limits on new research, Ask and RSS polling
- Offline test no longer reaches the live model
Docs: live links in README, decisions and spot check updated, email draft
moved out of the repository

### 28. Settings: mute, normal or boost each announcement type

The brief's ranking uses these settings directly; screenshots re-taken
(20 screens, 0 console errors, 0 accessibility or overflow issues).

### 29. Brief: one calm header

Short title, one line of counts, a small ring and an icon-only Play; the
quiet-window note moves under the window chips; the tip box becomes the
section hint.

### 30. Brief: bring back the original look

Glowing ring, mint selection, the quiet card with the FINN mark and the
large title, as the owner prefers; the week's cards and the latest
verified results follow below the quiet card.

### 31. Easier to find your way around, smoother motion

- Every nav tab shows its name; screens slide in the direction you move
- One plain line under each screen title says what it is for
- Company pages: back link and a sticky bar that jumps to Ask, Promises,
  Answers, Numbers, Bull/bear and Sources with smooth scrolling
- Section titles ease in as you scroll; buttons and rows respond to taps

### 32. New FINN mark and a lighter wordmark

The owner's F mark (two slanted bars) drawn as a vector icon, with the
app icons rendered from it; FINN set in a lighter, wider-spaced weight;
service worker cache bumped so installed apps pick up the new icon.

### 33. Header without the update time; logo files renamed so every device loads the new mark

### 34. Alerts: smaller rule sentence with room between its value pills

### 35. Alerts: backtest rows in two tidy lines

### 36. Research list: ticker, name and details on the left, verdicts stacked on the right

### 37. Build history: a readable log of how FINN was built

### 38. Opening animation: the F forms and the wordmark settles (about 2.5 s, once per visit, tap to skip)

### 39. Opening animation: works on iPhone Safari, starts from a plain screen

Each bar is its own small SVG moved as an HTML element (Safari handles
transforms on SVG paths unreliably), and the pre-load page no longer shows a
static logo that the animation then jumps away from.

### 40. Opening animation: hold a little longer and fade out gently

### 41. Opening animation without flicker on iPhone

The app is mounted only after the animation ends (an animated overlay above
blurred layers flickers in iPhone Safari), the animation starts once fonts are
ready, and the wordmark fades up instead of animating letter spacing.

### 42. Settings: AI cost moved to a compact section at the bottom; build totals kept

- Settings opens with the portfolio and announcement types; 'What it costs to
  run' is one line near the end, next to 'How FINN thinks'
- A cloud data refresh starts with an empty usage log; the shipped AI totals
  now keep the larger figure instead of shrinking to that run's
- Screenshot script: the Ask step targets the form button (the new jump bar
  also has an 'Ask' button, which had stopped the run partway)

### 43. Slimmer bottom bar: smaller icons and labels, lighter glow

### 44. Bottom bar with depth: lit top edge, shaded underside, lift shadow, raised pill

### 45. Remove Play my brief

The phone's built-in voice sounded mechanical; the Brief header keeps the
ring, title and counts. Docs and decisions updated.

### 46. Company names shown in a small highlighted chip on cards and rows

### 47. Softer accent and a plain background

Neon mint (#7CF29A) becomes a calmer sage-mint (#66D19E) everywhere, glows
are lighter, red is softer, and the green-tinted background is now plain
near-black with one faint tint behind the logo.

### 48. Brief: show 'Since last look' and '3 days' only when they hold something that needs attention

Otherwise the window chips are 24h, 7 days and Custom.

### 49. Settings: announcement types as a sliding toggle

A recessed track with a raised thumb that slides to the choice; unselected
options are readable, Boost turns mint, and the section says 'tap to change'.

### 50. Settings: Mute has its own soft red, so the three choices look distinct

### 51. FINN's take: one line at the top of each company page, built by Python

Promises kept, growth trend (3-year average vs latest quarter), margins,
a one-off jump in revenue, dodged questions, debt and cash conversion, each
coloured by whether it is good or bad news. Computed for new research and
recomputed for the cached and built-in companies without model calls.

### 52. Queue position for new companies: '1 ahead of you · about 4 min'

### 53. Daily refresh keeps each company's previous data when its own fetch fails

Briefs: a company whose filings sources all failed keeps its previous cards
inside the new window (marked carried over); prices: a stock whose fetch
failed keeps its previous series; research list: companies not produced this
run keep their previous rows.

### 54. Company charts: metric label and tap-to-see values; calls named by quarter (Q2 FY27)

### 55. Bank numbers for lenders: NII, margin on assets, NPA ratios when reported, deposits

From the statement tables only: NII = interest earned - interest paid, an
approximate NIM (annualised NII / total assets, labelled as such), gross and
net NPA where the tables have them, deposits and growth; 'Total income'
instead of 'Revenue' for lenders. CASA and the credit-deposit ratio are not
in these tables, and the page says so instead of guessing.

### 56. Pre-researched TCS, SBI, Bharti Airtel and ICICI Bank (open instantly; in the seed)

Maruti and Sun Pharma were already built in. 25 companies in total.

### 57. Docs: FINN's take, bank numbers, and why directional promises wait

### 58. Prettier charts

Revenue chart: gradient bars that grow in, dashed gridlines, a smooth margin
curve that draws itself with a soft fill and dots, and the selected year's
value on top. Cash chart: gradient bars, baseline and a legend. Promise
target band: soft track, gradient band, and the actual marker slides in,
green when the target was met, red when not. Alert strip bars rounded.

### 59. Date picker: boxes fit the card, quick picks wrap, dates as '1 Nov 2026'

### 60. Brief top: a slim 'Today: nothing new' line, then 'Earlier this week' with the 7-day cards

### 61. Cards show 'your X% holding' instead of the score; the score stays inside Why?

### 62. Visible 'Done' button next to Why? on each card (swipe still works)

### 63. Tapping a company name anywhere opens its Research page

### 64. Alerts: recent alerts first, the rule setup below

### 65. Report card: 'questions answered' instead of 'dodged'; zero tiles greyed out

### 66. Research landing: 'Your holdings' first, then 'Other companies'; one-line explainer

### 67. Unverified results cards say 'Results filed · numbers not verified', with the filing subject below

### 68. Company page: Ask box moved to the end (and last in the jump bar)

### 69. Brief header: a thin filter funnel, e.g. '20 filings → 3 worth knowing → 1 need you'

### 70. One sentence above each chart, written by Python from the chart's numbers

e.g. 'Revenue +16% YoY in Q2 FY27; profit +27%; operating margin 11.0%
(-2.0 pts).' and 'Cash from operations matched or beat profit in 4 of the
last 6 years.'

### 71. Brief: one-line portfolio pulse (holdings ahead of / behind the Nifty this week, biggest move)

### 72. Charts: older years grey, latest two highlighted, first and last values labelled, margin as a soft shaded area; net profit chart added

### 73. Card footer: the Filing link is the same size as Why? and Done

### 74. Alerts strip: slightly brighter bars with a tiny light dot on top

### 75. Alerts strip as peaks: each bar rises to that day's biggest move, with a glowing tip

### 76. Alerts peaks: greener bars and glow

### 77. Settings toggle: smooth eased slide instead of a springy bounce

### 78. Settings toggle: a gentle, slight bounce

### 79. Ask: full-size button, shorter placeholder, suggestions wrap instead of being cut off

### 80. Cash quality: one bar per year of cash per ₹1 of profit against a 1× line (green at or above, amber below)

### 81. Company pages: a 90-day 'mountain' chart of the stock vs the Nifty 50

The stock's % change as a filled area with a soft gradient, the Nifty as a
thin line, end values labelled; the series is computed in Python from
adjusted closes and stored with each company's research.

### 82. Laptop screens: a side panel saying FINN is built for your phone, with the link and what each tab does

### 83. Revenue and profit charts as mountains: smooth line with a soft filled area, dots, margin as a dashed line

### 84. Mountain charts: glowing white dots on the peaks and at the latest point

### 85. Laptop side panel: QR code that opens the app on a phone

### 86. Mountain charts from real points: straight segments, strong gradient, white dots on every peak

- 90-day price: green mountain for the stock, dashed grey Nifty, title like
  'LT +1.4% vs Nifty +3.5%' (green when ahead, red when behind)
- Revenue and profit mountains without smoothing; operating margin as its
  own gold mountain (net margin for lenders)
- Cash quality: green mountain of cash earned per ₹1 of profit against a
  dashed ₹1 line, with the Python verdict above; skipped for lenders

### 87. Revenue and profit back to bar charts (older years grey, latest two green); mountains only for price, margin and cash quality

### 88. Only cash quality is a mountain: revenue and profit as bars, 90-day price chart removed

### 89. Build log rewritten: research, method and reasons by phase; author-designed logo

### 90. Build log: design thinking section

### 91. Laptop: just a small QR in the corner

### 92. Build log: the full step-by-step working story

### 93. Build log: plain narrative of the reasoning, method, testing, decisions and fallbacks

### 94. Build history in five parts: research, data and brief, research engine, design and UX, deployment

### 95. Build history: the logo's design and meaning, earlier analysis with Claude and Gemini, setup

### 96. Build history part 6: my instructions at each stage and what the AI did

### 97. Build history part 6 in a natural voice
