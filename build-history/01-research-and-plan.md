# Part 1: Research, first principles and the plan

This is the first of five parts describing how I built FINN with AI. It covers
everything that happened before the first line of production code: the research
and analysis I did across earlier AI threads, the hypothetical prototype that
came out of them, and how that work became the plan for the real build.

Lines starting with ">" are my everyday instructions to the AI, tidied up but
kept to what I actually asked. Lines starting with "●" are what the AI did,
found or recommended in response, and what I decided.

| Part | What it covers |
|---|---|
| 1 | Research, first principles and the plan (this file) |
| 2 | Real data and the push engine (the brief) |
| 3 | The research engine (pull) |
| 4 | Designing the app and the user experience |
| 5 | Deployment, fallbacks and the finish |

---

## 1.1 How I organised the thinking

> dont start making the app yet. first i want proper analysis of this challenge,
> do it in separate threads so each one goes deep. one for strategy, one for
> data, one for push, one for pull and one for the frontend. each one should
> give me something i can actually use when we build

● I split the early work into five AI threads on purpose. A single conversation
  that tries to do strategy, data plumbing and UI at once ends up shallow on all
  three. Separate threads let each one go deep, and let me compare their outputs
  before committing to anything.

| Thread | Question it answered | What it produced |
|---|---|---|
| 1. Strategy | What should FINN be, and why would it win? | A 20-page solution strategy |
| 2. Data | Which sources actually work, and how do we get from them? | A data-layer prototype (finn-data) |
| 3. Push | How do we decide what deserves attention? | A push-engine prototype |
| 4. Pull | How do we research a company honestly? | A research-engine prototype (finn-pull) |
| 5. Frontend | How should an investor actually interact with it? | A mobile UI prototype (finn-mobile) |

● I didn't rely on one model for this. Alongside the Claude threads, I ran
  several separate analyses with Gemini on the same questions, so I could
  compare two models' takes on the brief, the approach and the risks before
  committing to anything. Where they agreed, I moved faster. Where they
  disagreed, I looked closer.

● Together these became my starting kit: the strategy document, the hypothetical
  prototype code from the four build threads, and two UI reference images
  showing the look I wanted. Everything in the real build grew from that
  analysis.

---

## 1.2 Reading the brief like a grader

> read both the enam pdfs line by line. tell me what they are asking, what they
> will actually judge us on, what we cant break and what they are hinting at. we
> should make it for how they will grade it, not just the feature list

● The strategy thread tagged every sentence of the brief. The key finding was
  that what ENAM grades (creativity, product sense, judgment, architecture) is
  different from the feature list, and they say outright that they are not
  grading completeness or polish.

● The hard constraints: mobile-first and easy to try on a phone; a portfolio of
  15 to 20 NSE/BSE names plus 3 to 5 research names; research that generalises
  to any NSE ticker, including one they choose; the pull side grounded only in
  primary sources, not the model's own knowledge; configurable alert thresholds;
  a digest window the user can choose.

● The hidden signals were the most useful part. A few examples of what the brief
  says and what it is really testing:

| What the brief says | What it is really testing | Our response |
|---|---|---|
| The backend is "plumbing, not the point" | Will you over-engineer the boring part? | Simple scheduled jobs and SQLite. No message queues, no vector database |
| For results, show Revenue, EBITDA, PBT, PAT, QoQ, YoY | Can you extract numbers reliably from messy PDFs? | Extraction plus arithmetic checks and a cross-source check, with a "verified" badge |
| "For every other type, decide what earns my attention" | Judgment. There is no right answer, only a defended one | A published treatment table for all 17 categories |
| Promised vs delivered is "the kind of thing we value most" | Analysis over summary | The Promise Ledger becomes the hero of the research page |
| "Don't lean on the model's outside knowledge" | Do you understand LLM failure modes and enforce discipline in code? | Retrieval-only context, verbatim quote checks, an "insufficient evidence" state |
| "We may point it at a company you didn't pick" | Is it a demo or a system? | A cold-start pipeline with no company-specific code |
| "No AI slop. Density and design both count" | Will the UI be a wall of generated paragraphs? | Hard character budgets per field; numbers in tables |

● One timing insight shaped the whole demo. SEBI gives companies 45 days after
  quarter-end to publish results, so the July to September quarter's results
  land by about 14 November. The submission window sat at the peak of results
  season. That meant the live feed would be full of results filings and
  earnings-call transcripts, so the Results card and the Promise Ledger were the
  two features to nail, and they would have fresh, real data on demo day.

---

## 1.3 First principles

> forget all the investing apps that exist. think from first principle what is
> actually true about an investor, a filing, a phone and an llm. make each of
> those a rule for how we design

● The strategy thread came back with six truths, each one turned into a rule:

| # | What is true | The rule it produced |
|---|---|---|
| 1 | Attention is the scarce resource, not information. An investor with 18 holdings in results season faces around a hundred filings a week, and perhaps a handful change their view | Rank by materiality, not time. Show a small fixed number of hero items and collapse the rest to counts |
| 2 | Materiality is relative. A 3% move is large for a bank and routine for a high-beta small-cap. A CFO exit matters more than an independent director's | Thresholds are per stock (relative to its own volatility) and per role, never global constants |
| 3 | Trust is earned with evidence. One wrong number destroys a finance tool, and LLMs are fluent before they are correct | Numbers come from tables and are cross-checked. Every claim links to a source page. If evidence is missing, say so |
| 4 | The phone is used in glances: short, one-handed, interrupted sessions where typing is expensive | The home screen needs zero typing. Gestures do triage. Depth is opt-in |
| 5 | Cost scales with documents, not users. A filing is the same document for everyone who holds the stock | Process each document once, key the result by content hash, and share it. Personalisation is cheap ranking on top |
| 6 | The exchange already half-classifies its filings with standard subject lines | Deterministic rules first; pay for an LLM only when the rules are unsure |

● One insight from this step changed a feature completely. I had assumed the
  background of a new CFO would have to come from the web. The analysis found
  that SEBI's disclosure rules already require a listed company to include a
  short profile of a newly appointed director or key managerial person in the
  exchange filing itself. So the first source for "who is the new CFO?" is the
  primary document: free, reliable and permitted. We decided not to scrape
  LinkedIn, because it breaks their terms and is brittle.

● The thread also wrote down what "best in the world" means for this product,
  and I used that sentence as the test for every later decision: the best
  version of FINN is the one where an investor opens it at 7:30 in the morning,
  spends ninety seconds, and knows with confidence either that nothing important
  happened or exactly which one thing did.

---

## 1.4 Brainstorming twelve interaction models

> before we choose anything brainstorm properly. give me atleast 12 different
> ways an investor can use finn, even weird ones. then score them so we know why
> we picked one, not just by feel

● The thread used three brainstorming rules: quantity first (twelve concepts
  before judging any), invert the problem ("how would we make an investor miss
  the one filing that matters?" The answer: bury it in a feed sorted by time, so
  FINN never sorts by time alone), and borrow from other domains (inbox zero
  from email, severity-first from hospital triage, and the newspaper front page
  where an editor decides what goes above the fold).

● Each concept was scored from 1 to 5 on five weighted criteria: time saved
  (30%), differentiation (25%), buildable by the deadline (20%), demo-ability on
  a phone (15%) and trust (10%).

| Concept | Idea in one line | Score /5 |
|---|---|---|
| Since-you-last-looked Brief | Front page of your portfolio, editor-ranked, routine collapsed | 4.6 |
| Promise Ledger | Guidance vs delivery, quarter by quarter, with quotes | 4.3 |
| Triage gestures | Swipe right = done, left = less like this, long-press = why | 4.1 |
| Event × price linking | "Moved −6% on 3× volume, 2 hours after this filing" | 3.9 |
| Thesis tracker | Each holding has a written thesis; flag filings that threaten it | 3.6 |
| Read-aloud brief | A 60-second spoken brief using the phone's built-in voice | 3.55 |
| Contextual "Ask about this" | Q&A scoped to one card or company, with citations | 3.25 |
| Heat-map pulse | Portfolio as a grid coloured by event intensity | 3.05 |
| Messaging bot | Brief delivered in a chat app | 2.9 |
| Lock-screen widget | One line: "1 material item today" | 2.85 |
| Dashboard of tiles | Prices, heatmap, counts | 2.6 |
| Chat-first copilot | One chat box for everything | 2.55 |

● The convergence decision: take the top three as the core, fold in two cheap
  high-value ideas (event × price linking, which reuses data we already had, and
  the read-aloud brief, which costs nothing in model spend), and keep "Ask about
  this" only as a scoped escape hatch inside cards and the research page.

> chat app is the obvious idea, so first argue for it properly. if we are not
> doing it i want to know exactly why

● The case for chat-first: flexible, familiar, quick to build, handles any
  question. Why we still rejected it as the front door: it makes the investor do
  the filtering by asking, which is exactly the job the brief gives to FINN;
  nobody can ask about a filing they don't know exists; typing on a phone is the
  slowest input there is; and every chat-first submission will look the same.
  Chat survived only as a scoped tool, where it has context and gives better,
  cheaper answers.

---

## 1.5 The point of view: Glance, Scan, Dig

> they said best submissions have a point of view on how an investor uses it.
> give me that in one line and make every screen follow it

● The point of view became three depths, each about ten times deeper than the
  last, where the investor always chooses how far to go:

| Level | Time | Where | What it shows |
|---|---|---|---|
| Glance | 3 seconds | The top of the brief | "2 things matter today." Nothing else |
| Scan | 30 to 90 seconds | The brief | Type-specific cards, routine collapsed, swipe to clear |
| Dig | 5 to 10 minutes | The research page for one company | Snapshot, trajectory, balance sheet, cash quality, Promise Ledger, bull vs bear, scoped Q&A |

● Every level answers the same four questions: what changed, why should I care,
  what is the evidence, and what can I do next.

● The interaction details that carry this point of view were written down at
  this stage too:
- Gestures, not menus. Swipe right to clear a card (inbox zero for a portfolio).
  Long-press for "why am I seeing this?", which shows the score's parts.
- The time window is a first-class control: chips for 24 hours, 3 days, 7 days
  and a custom range, as the brief requires.
- The header shows the filter itself, for example "41 filings · 3 matter".
  Showing what was hidden is what makes hiding trustworthy.
- Price links are framed as "filed before the move", never "caused by". If
  nothing was filed before a big move, the app says so, because an unexplained
  move is useful information too.
- Copy budgets keep it free of AI slop: a card headline of 70 characters or less
  with no adjectives unless a number supports them; a summary of 140 characters
  or less; ledger quotes word for word with document and page; bull and bear at
  three bullets each, every one citing a number or quote.

---

## 1.6 The filter, written down so it can be argued with

> decide what earns my attention is the real test here. write our judgment for
> all 17 types with a score and what changes it, so anyone can disagree with a
> line and not just a feeling

● The thread produced a treatment table for every category. A few rows show the
  kind of judgment it encodes:

| Category | Base | Treatment | What moves the score |
|---|---|---|---|
| Results | 0.95 | Hero card | Results ads and board-meeting intimations are reclassified to collapsed |
| M&A | 0.85 | Hero card | Deal size as a share of market cap scales it; small subsidiary infusions drop to one-liner |
| Management change | 0.70 | Hero card | CEO/MD/CFO ×1.3; independent director ×0.5; unexplained mid-term exit ×1.2; planned retirement ×0.8 |
| Credit rating | 0.60 | Hero or collapsed | Downgrade or outlook cut = hero; upgrade = one-liner; reaffirmation = collapsed |
| Pledging | 0.55 | One-liner or hero | An increase in pledged shares = hero; a release = one-liner |
| Dividend | 0.25 | Collapsed | Special or unusually large dividends promoted |
| Investor meetings | 0.10 | Collapsed | Counted only |
| Unclassified | 0.05 | Hidden | Still counted in the header, so nothing is secretly dropped |

● The score formula came from the same step: materiality = base × modifiers
  (role, direction, size) × holding weight × user preference + a bonus if the
  market reacted unusually. A user's preference can move between 0.5 and 1.5
  only, so nobody can silence results entirely by accident. These are the exact
  rules the real engine implements in Part 2.

---

## 1.7 Choosing the portfolio so it tests the system

> you pick the portfolio but every company should be there for a reason, it
> should test some different part of finn. sector and size should come from that

● I asked Claude to pick the portfolio with that rule, and it chose the 18
  names. I checked each one against what it was meant to test. They were chosen
  as test cases, not favourites. Some examples of what each one tests:
- Reliance: a multi-segment conglomerate, to test segment parsing.
- HDFC Bank: a bank, so no EBITDA. Also a company that gives little explicit
  guidance, which tests the ledger's empty state.
- Infosys: gives an explicit revenue and margin band every quarter, so it is the
  cleanest Promise Ledger demo.
- L&T: order-inflow and margin guidance, plus frequent order-win press releases
  to rank.
- Maruti: monthly sales releases, which are high-frequency routine filings that
  must collapse cleanly.
- ITC: dividend-heavy, to test that routine dividends stay collapsed.
- Bajaj Finance: an NBFC with credit-rating filings.
- Vedanta: leverage, pledging and credit ratings.
- Suzlon: high volume and volatility, the "relative to its own normal" alert
  demo.
- MapMyIndia: a small cap with sparse filings, which proves FINN does not invent
  importance when little happens.
- Persistent and Happiest Minds: two more IT formats, so the engine is not tuned
  to one company's layout.

● The research names were chosen for tension: Asian Paints (a narrative under
  pressure from new competition), Paytm (a loss-to-profit journey that tests
  sign handling), HAL (order-book guidance and lumpy revenue, which shows why
  the ledger says "Too early" mid-year) and Trent (high expectations make
  promised vs delivered sharp). The fifth research name was deliberately left to
  the grader, through a live search box.

---

## 1.8 Architecture: boring where it can be, clever where it matters

> keep backend simple, it shouldnt become the whole project. tell me why we dont
> need vector database or agent framework so i can explain it to someone

● The architecture was three lanes: ingest once (prices, announcements and
  fundamentals on a schedule), enrich once per document (classify, score, enrich
  by type), and serve many (a small API with precomputed briefs).

● Why no vector database: one company's documents (an annual report plus four to
  eight transcripts) are a few hundred thousand tokens. Section-aware chunking
  and keyword search, plus a cheap first pass, cover retrieval without new
  infrastructure.

● Why no agent framework: the pipeline is a fixed sequence of steps. Plain
  Python functions are easier to debug, test and cost-control than an agent
  loop. An agent earns its cost only when the path is unknown in advance, and
  here it is known.

● Generalising to any ticker: resolve the symbol, fetch the tables in seconds,
  render the sections that need no model immediately, then stream in the Promise
  Ledger and bull/bear as they finish. No company-specific code paths; the demo
  set only pre-warms the cache.

---

## 1.9 Model routing, cost and trust

> efficiency gets bonus points. use cheapest thing that works, go to the bigger
> model only if a check fails. tell me the cost before we spend anything

● The routing rule: deterministic code first, a small model for volume, and a
  strong model only where reasoning is the product. Category from the subject
  line uses rules; ambiguous filings and one-line summaries use the cheap model;
  results extraction uses the cheap model and escalates only if the arithmetic
  checks fail; promise verdicts use the strong model, once per company per
  quarter.

● The cost estimate, written as working numbers to be replaced by measured logs:
  about $0.06 a day for push in results season, about $0.10 to $0.17 for a cold
  research run, and nothing at all once cached. Five cache layers were designed:
  documents by content hash, enrichments by document and prompt version,
  research by company and latest document date, a prompt cache for follow-up
  questions, and daily price statistics.

● The router was designed as a configuration file, so the build could swap in a
  free-tier provider without code changes. That turned out to matter, because in
  the real build I chose to run the whole app on Gemini's free tier (see 1.12).

> primary sources only should be in the code, not just asking the model nicely.
> list every way the model can mislead an investor and how we stop it

● The trust table covered: the model using outside knowledge (only retrieved
  excerpts with IDs, and every claim needs a source ID or it is removed);
  invented or paraphrased quotes (every quote checked word for word against the
  cited page); wrong numbers from PDF tables (arithmetic identities, period
  order, units, consolidated vs standalone, a cross-check with Screener);
  confident analysis on thin evidence (explicit "Too early" and "Insufficient
  evidence" states); investment advice (FINN never says buy or sell and has no
  price targets, so the investor stays the decision maker); and prompt injection
  through filing text (filings passed as delimited data, outputs
  schema-validated, no tools exposed on the enrichment path).

● An evaluation plan was set at the same time: hand-checked results filings
  across formats, about 100 hand-labelled filings for classification, and a
  human reading of three companies' promises. Showing an evaluation is one of
  the clearest signals of engineering judgment, so I wanted real numbers in the
  repo, not claims.

---

## 1.10 Red-teaming the plan

> do a pre mortem. say the demo failed on submission day, what are the most
> likely reasons and how do we stop each

● The pre-mortem listed failure modes and mitigations, and several became hard
  rules for the build: the exchange may block automated requests, so seed a
  frozen snapshot so the demo runs regardless; free servers sleep, so keep one
  warm during the review window; the grader may pick a company we never tested,
  so build the cold path first; and "a demo that doesn't run is the worst
  outcome", so deploy early and cut features in a pre-agreed order instead of
  shipping something half-built.

---

## 1.11 The hypothetical prototype

> now make a rough prototype of each part from this analysis so we know what is
> hard before the real build

● The four build threads each produced a working sketch:
- finn-data tested how to get prices, filings and fundamentals, and where each
  source breaks.
- push-engine implemented the ordered classification rules, sub-types and base
  scores from the treatment table.
- finn-pull sketched the research pipeline: tables first, then promise
  extraction and verdicts.
- finn-mobile sketched the Brief, the cards and the research page as a phone UI.

● The prototype was never meant to be the product. Its job was to turn the
  strategy into something concrete enough to criticise. When the real build
  started, I gave the AI the whole kit (the strategy document, this prototype
  code and my UI reference images) and asked it to treat it as a starting point
  to improve, not a specification to copy.

---

## 1.12 Starting the real build from the analysis

> I am working on this i need to make the app for this. think and ideate well.
> use first principle thinking, do deep analysis, use the ideas of brainstorming
> to decide what exactly should be in the app then start working. keep
> explaining me what you are doing and ask me before any major step. i dont know
> abt app making so explain me in simple language. i also did research on this,
> look into that as well. break your work into tasks and do it one by one

● The AI read the brief, the strategy and the prototype, and came back with a
  first plan. I read it and pushed back.

> it sounds a bit weak rn so keep analysing as u go ahead, keep looking for
> better and efficient ways. i dont want fast app, i want great app that can
> actually stand out

● That push changed the plan in a specific way. Instead of freezing the analysis
  and executing it, the analysis kept running alongside the build. Several of
  FINN's strongest details came from that: the per-stock alert default came from
  a backtest instead of the strategy's suggested presets, the promise verdicts
  moved from a strong model's judgement to Python rules after a hand check, and
  the "Why?" card became the main way the app explains itself.

● Two things from the analysis changed once real data and real constraints
  arrived:
- The model provider. The strategy had assumed paid Claude models for routing
  (Haiku for volume, Sonnet or Opus for reasoning). The AI laid out the options
  on a decision card and I chose the Gemini free tier, so a reviewer can use the
  app without a bill growing behind a public link. Because the router was
  designed as configuration, this was a settings change, not a rewrite. Gemini
  Flash-Lite took the cheap jobs and Gemini Flash took the hard reading. Across
  the whole build that came to roughly 376 model calls and 1.1 million tokens,
  at zero cost.
- The exchange APIs. The strategy planned to read the NSE and BSE announcement
  endpoints. In the real build they refused automated access, and I decided to
  respect that instead of working around it. Part 2 explains the honest route we
  built instead.

> write the rules down first so nobody drifts. primary sources only, no going
> around bot protection, never commit keys, model never does maths, quotes
> checked word for word. and log every trade off with what it cost us

● Those rules went into CLAUDE.md, which the AI reads at the start of every
  session, so I never had to repeat them. Every trade-off went into DECISIONS.md
  as "decision, why, what we gave up". By the end it had more than sixty rows.

● The work was split into six tasks, each ending with something running on live
  data and a written report I could check: setup, data pipes, push engine, pull
  engine, the app, and the submission.

---

## 1.13 Setting up how the AI and I would work

> why are you not working yourself on the vs code. i want you to work in my
> project and run things yourself, not give me code to paste

● The cloud session was connected to the GitHub repository, and a Remote Control
  session was set up on my laptop so the AI could write files, run tests, start
  the app and push using my machine and my own sign-ins. When the access setup
  asked me to add a collaborator account I didn't recognise, I stopped and
  switched to a clean sign-in under my own account instead.

● One limitation shaped the workflow: the laptop session only sees what I type
  into it, and the cloud session cannot talk to it directly. So we used a split.
  The cloud session planned, reviewed and wrote exact, paste-ready instruction
  blocks; I pasted them into the laptop session, which built, tested and
  reported back. One AI thought and checked, the other executed, and I stayed in
  the loop for every change that reached the repository.

> first you finish all the deliverables, then i will check it on the app. i dont
> want to see half built screens

● Reviewing half-finished work spends attention and AI budget on feedback the
  next change makes obsolete. So the rule was: build the whole thing, then I
  review it on my phone in one pass, then we iterate. That review is where Part
  4 begins.

> if you'll work overnight, do we have enough credits to finish it? optimize and
> keep working, be mindful of credits

● I treated AI usage like money from the start. The strongest model was used for
  architecture, judging promises and critical review; a smaller model for
  mechanical changes; and instructions were written as precise numbered lists so
  the AI spent its effort building rather than guessing.

---

## 1.14 What I took away from this part

● The most valuable thing I did with AI happened before any code: splitting the
  thinking into separate deep threads, making the AI read the brief like a
  grader, forcing it to brainstorm twelve options and score them, and
  red-teaming the obvious choice.

● Writing judgment down (the treatment table, the trust table, the cut order)
  made every later disagreement concrete. When something felt wrong in the real
  build, I could point to a specific line and change it.

● I treated the analysis as a starting point. The build got better exactly where
  real data contradicted it, and I let that happen.

Next: Part 2, real data and the push engine.

