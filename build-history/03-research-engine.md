# Part 3: The research engine (pull)

This part covers the research side of FINN: what happens when an investor opens
any listed company and asks the question that actually matters to them, which is
whether management does what it says it will do. As in the other parts, lines
starting with ">" are my everyday instructions to Claude, tidied up but kept to
what I actually asked, and lines starting with "●" are what Claude did, found or
recommended, and what I decided.

---

## 3.1 Deciding what research should even mean

> every app shows snapshot, ratios and news. thats not research. i want the one
> page an investor will actually come back to. think what a serious analyst
> checks first and make that

● Claude started from the investor's real question instead of from available
  data. A retail investor reading about a company is mostly trying to decide
  whether to believe management. They hear confident statements on every
  earnings call, and they have no easy way to check later whether those
  statements came true.

● That led to the three pillars of the research page:
- The Promise Ledger: every measurable promise management made on earnings
  calls, quoted exactly with its page number, and graded later against what the
  company actually reported.
- Did they answer?: analysts ask hard questions on those calls. Which ones did
  management dodge?
- Bull vs bear from computed facts: the case for and against, but built only on
  numbers Python computed, never on the model's opinion.

● Around those pillars, the plain sections every investor expects: a snapshot,
  the multi-year trajectory, the balance sheet and cash quality.

---

## 3.2 Fast, free sections first

> page should show something in seconds even on a cold start. anything that
> doesnt need the model shouldnt wait for it

● Claude split the page into two kinds of section. The table sections (snapshot,
  trajectory, balance sheet, cash quality) use no model at all. They are
  computed straight from Screener's statement tables in Python, published first,
  and shown immediately. The model-dependent sections (promises, dodged
  questions, bull and bear) fill in afterwards.

● Real outputs from the first live run, to give a sense of what the table
  sections say:
- Reliance: 5-year revenue CAGR 17.8%, profit 12.2%; debt/equity 0.43; operating
  cash flow 2.07x reported profit over three years ("cash backs the profits").
- Infosys: debt/equity 0.09; operating cash flow 1.15x profit.
- HDFC Bank: "Lender: debt/equity and working-capital cycle do not apply." and
  "Lender: operating cash flow mostly reflects loan and deposit movements;
  CFO/PAT is not a quality signal."

● That last one mattered to me. Showing a cash-quality number for a bank would
  be technically computable and completely meaningless. Claude detected lenders
  from their own statement labels and replaced the metric with an honest
  sentence.

● Segments are marked "verified" only when they add up to reported revenue. For
  Infosys they matched exactly (178,650 cr vs 178,650 cr). For Reliance and HDFC
  Bank they did not, because of inter-segment eliminations, so they are shown as
  "unverified" with the gap printed next to them.

---

## 3.3 Reading earnings calls properly

> transcripts are the base for the whole research page. read them like an
> analyst, know who is speaking, separate management and analysts, and never
> misquote

● Every company formats transcripts differently, and the first runs showed how
  messy that is:
- a frequent speaker at Infosys (the CEO) was mistaken for a running page
  header, because his name appeared at the top of many pages;
- at HDFC Bank, the CFO was mistaken for an analyst.

● Claude fixed this with general rules rather than per-company code:
- speakers are found from the document itself, from recurring "Name:" lines or
  name-only lines, and running headers are only taken from the edges of a page;
- roles are worked out first from the moderator's introductions, then from the
  participant list, then from how each person behaves in the Q&A (who asks, who
  answers).

● A second problem: in one run, a cover letter attached to the filing was
  treated as the transcript. Fix: documents are classified before they are read.

● Quote checking also needed tuning. PDF text often breaks words with stray
  spaces ("gui dance"), so a strict match rejected quotes that were genuinely
  correct. Claude changed the check to ignore whitespace while every other
  character must still match exactly, and quotes that run over a page break are
  found too.

● Speed: one annual report took more than ten minutes to read. Long PDFs (over
  60 pages) now skip the slow fallback text reader, annual reports have a
  four-minute budget, and the reader runs in a background thread so one slow
  report can never hold up a finished job.

---

## 3.4 The Promise Ledger

> take out every promise from the calls with exact quote and page. model can
> find them but python gives the verdict. if quote is not there word for word,
> it doesnt exist

● Claude split the job by what each side is good at:
1. Gemini Flash reads the call and extracts each forward-looking, measurable
   statement made by management, with the exact quote, page, metric, target and
   period.
2. Python checks the quote exists word for word in the PDF. If not, it is
   dropped.
3. Python compares the target with the reported numbers and gives the verdict.
4. The one-line reason under each verdict is also written by Python, from the
   numbers.

● The verdicts:

| Verdict | Meaning |
|---|---|
| Kept | The number was delivered |
| Partly | It got close |
| Missed | It was not delivered |
| Too early | The period hasn't been reported yet |
| Quietly dropped | Management stopped mentioning it |
| Not measurable | No number in the tables to check against |

● A real example from Infosys: "Too early · ebit margin · FY27 · target 20-22% ·
  said Oct call, p.30 · FY27 has not been reported yet". Three Infosys
  statements were scorable later; ten more were tracked but not measurable from
  the tables, and the page says so instead of guessing.

---

## 3.5 The hand check that changed everything

> dont trust the verdicts just because they look right. check them with the
> transcripts by hand, start with the hardest companies, and tell me how many
> are actually right

● Claude read every statement the engine had extracted for L&T (20 statements
  across 5 calls) and HAL (25 statements across 5 calls) against the transcript
  pages, and then checked every scored verdict across all six research
  companies.

● Extraction was perfect: 45 of 45 extracted items were genuine forward-looking
  statements by management (not by an analyst, not about the past), and every
  quote was found word for word on the page cited.

● The verdicts were not. On the first pass, only 4 of 7 scored verdicts were
  right. The errors, and the general rule each one became:

| # | Company | What went wrong | General fix |
|---|---|---|---|
| 1 | L&T | An 8.5% margin target for the core projects business was compared with the group margin, and wrongly marked Kept | Promises carry a scope (company or a named segment); only company-wide targets are measured against company-wide tables |
| 2 | L&T | The same target restated as "EBITDA" instead of "EBIT" was marked Quietly dropped | Margin types form one family for the drop check |
| 3 | HAL | "FY24-25" and "'26-'27" were read as the first year | A fiscal range names the year it ends in |
| 4 | HAL | A company-wide 10-11% target was merged with a 9-10% repair-business target | Company and segment targets are separate trails |
| 5 | HAL | A later vague "double-digit growth" erased the earlier "10% to 11%" | The verdict uses the latest statement that has a number |
| 6 | Infosys | 3-3.5% guidance in constant currency was compared with rupee growth and marked Kept | The full source sentence is checked for constant currency or USD; such guidance is Not measurable, because converting would invent a number |
| 7 | Titan | A 13-14% target for a narrower part of the business was compared with a 44.9% actual and marked Kept | An actual far above target is not scored and is flagged as a likely scope mismatch |

● After the fixes, 8 of 8 scored verdicts across the six companies matched the
  hand reading. Because the fixes are general rules, Claude was careful to say
  this is in-sample, and that line is in the report.

● This was the single most important moment of the build for me. The model's
  extraction was flawless, and the verdicts still looked confident and were
  still wrong almost half the time. Only a hand check caught it. Since then,
  every verdict feature in FINN has had a hand check before it shipped.

---

## 3.6 What the ledger actually found

● When the research side was done, Claude reported real findings, using only the
  companies' own transcripts, annual reports and results:
- Kept: HAL said its EBITDA margin would be "somewhere around 30%-31%". It came
  in at 31.1%.
- Missed: L&T promised 15% revenue growth for FY26 on three separate calls and
  delivered 11.8%. HAL guided 10-11% growth for FY25 and delivered 2.0%.
- Dodged: an analyst asked Infosys about a security breach, and the answer was
  "I do not have any specific comments on it right now" (transcript page 17).
- Story vs numbers: Asian Paints' CEO called growth "very strong" while the
  operating margin was down 2 points year on year.
- Report cards: HAL kept 3 promises, partly kept 2, missed 1, and dodged 1 of 26
  questions. L&T dodged 0 of 40.

● Later, the Ask box was tested on the same promise: asked "Did they hit their
  revenue guidance?" on L&T, it answered "No, the target was 15% and the actual
  was 11.8%", with a link to the source.

## 3.7 Quietly dropped

> quietly dropped is a big accusation on management. make it hard to trigger, it
> shouldnt fire because of a misunderstanding

● Claude set the bar high: a promise is quietly dropped only when two later
  calls, both before the deadline, say nothing at all about that metric. One
  quiet call only means "not repeated yet". A metric discussed for a different
  period does not count as dropped.

● The cost is that a real drop is flagged later than it could be. I chose that,
  because a false accusation on a company page is far worse than a slow one.

---

## 3.8 Did they answer the question?

> flag the questions management dodged, but only when the proof is in the quoted
> answer. i rather have less flags that are always right

● A judge model reads each analyst question and management's answer and labels
  it answered, partly or dodged. It may say "dodged" only for a clear
  non-answer. Python then keeps the label only if the quoted answer itself shows
  a refusal or deflection, or a number was asked for and the whole answer
  contains none. A request to repeat the question is never a dodge.

● The first run flagged an analyst asking HAL "which programme?" as a dodge,
  which is obviously a clarification, not an evasion. That is what led to the
  stricter judge and the Python evidence rule.

● Results on the six research companies: 224 question-answer pairs with verified
  quotes; 214 answered, 8 partly, 2 dodged. Python downgraded one model "dodged"
  that had no evidence behind it.

● Hand check of 15 labels against the transcripts: 12 agreed. Both "dodged"
  labels in the sample were right (for example Infosys: "I do not have any
  specific comments on it right now"). Every disagreement leaned toward not
  accusing management, which is the trade-off I asked for. Later, all four CDSL
  "dodged" flags were read by hand and every one was an explicit refusal
  ("that's a forward-looking statement, so we will not be able to comment").

---

## 3.9 Narrative vs numbers

> catch when management sounds happy about something the numbers say is getting
> worse. no model opinion, make it mechanical

● Claude made this fully deterministic. In the latest call, present-tense upbeat
  words about a metric are matched against that metric falling year on year in
  the tables. Forecasts and hedged sentences are excluded.

● A real example from Reliance: a speaker described "a fairly healthy margin
  expansion of almost 200 basis points" on p.5, while the company's operating
  margin was down 1.0 point year on year in the same quarter. The page shows
  both side by side and lets the investor judge.

● It misses subtler divergences, and that is written down. But everything it
  does flag is checkable.

---

## 3.10 Bull vs bear, from facts only

> bull and bear should stand on numbers python computed. model can write them
> but it should never decide which side a fact goes

● Python first builds a numbered pool of facts: latest growth, growth against
  the 3-year trend, margin direction, whether profit growth lags revenue growth,
  debt, cash and consistency (for example "revenue grew YoY in 8 of 8 recent
  quarters"). Each fact is marked with the side it supports.

● Flash-Lite phrases the bullets from that pool, and Python keeps only bullets
  that cite a real fact with matching numbers. The bullets are plain, but each
  one stands on a number.

● A review pass caught a positive number sitting in the bear column (HDFC Bank's
  "+9.4% YoY revenue" listed as a bear point). That is why each fact's side is
  now fixed in Python and the model cannot move it.

● Claude then added Python-computed comparisons that make the case sharper:
  growth slowing against its 3-year trend, margins squeezed, profit lagging
  revenue.

---

## 3.11 The HDFC Bank merger trap

> hdfc bank growth looks huge because of the merger. finn shouldnt sell merger
> as normal growth, and it shouldnt punish a company that is actually growing
> fast

● HDFC Bank's 3-year revenue CAGR came out at 26.9%. That includes the merger
  with HDFC Ltd, so it is not like-for-like.

● Claude's method: a merger paid in shares increases the share count, so
  earnings per share grow much more slowly than revenue in a merger year. FINN
  confirms a merger-sized jump through that per-share dilution and labels the
  growth "not like-for-like". A fast organic grower, whose EPS keeps up with
  revenue, is not flagged.

● The known gap: a merger paid in cash does not dilute, so it would not be
  caught. That is written down.

---

## 3.12 FINN's take

> put one line on top of every company page that tells the story in 5 seconds.
> make it from facts already checked on the page so its never a new claim

● Python writes the line from the page's own verified facts: how many targets
  are tracked and kept, growth against its 3-year average, margin direction,
  questions dodged, debt and cash. For example: "9 targets tracked · growth
  slowing 29% → 10% · margins widening · dodged 1 of 27 questions".

● The wording is plain. I accepted that, because a summary line written freely
  by a model would be the one unchecked claim on an otherwise fully checked
  page.

---

## 3.13 Ask about this company

> add an ask box but it should only answer from finn's checked evidence and cite
> it. if evidence doesnt cover it, it should say so

● The model sees only a numbered list of evidence (facts, ledger quotes,
  dodged-question quotes, segment data) and must cite the numbers it uses.
  Python re-checks every number and every praise word in the answer. If
  something doesn't match, the answer becomes "not covered by these sources".

● It deliberately declines general questions. A chat box that could say anything
  would undo every other check in the app.

---

## 3.14 Any company, instantly

> they may test a company we never picked. any nse ticker should work live,
> likely ones should open instantly, and free quota shouldnt die if many people
> use it

● Research is cached by company and by the date of its newest source document,
  so a company is only re-read when it files something new.

● Likely picks are read in advance and stored in a seed that ships with the
  backend: 21 companies at first, and later 25, after I asked for TCS, SBI,
  Bharti Airtel, Maruti, Sun Pharma and ICICI Bank to open instantly. Maruti and
  Sun Pharma were already in my portfolio, so TCS, SBI, Bharti Airtel and ICICI
  Bank were read in, watching the free Gemini quota while doing it.

● Any other NSE company is read live, one job at a time to protect the quota.
  The user sees their place in the queue and an estimate, for example "1 ahead
  of you · about 4 min".

● One data export took more than 90 minutes, most likely because a site asked us
  to retry much later. Retries now use a short backoff and fall back to the
  cache instead of waiting.

---

## 3.15 What I held back

> directional promises like margins should improve, can we check those also?

● Claude explained the problem: the extractor skips vague statements by design,
  so grading them would mean re-reading every call and hand-checking every new
  verdict. On the final night, that could not be done safely.

● Claude checked how many such promises had actually been saved: only 4, all due
  between 2028 and 2032. Doing it properly meant re-reading every earnings call
  that night, and the new verdicts wouldn't be checked by hand before I
  submitted. It recommended skipping it.

> okay as u recommend

● So it was held back and listed as the first item under future work. A wrong
  "Missed" on a company page is worse than no verdict at all.

## 3.16 Bank numbers

> bank numbers for lenders like hdfc bank, nii, nim, npa, casa, credit deposit
> ratio, and total income instead of revenue

● HDFC Bank, SBI, ICICI Bank and Bajaj Finance got a "Bank numbers" card with
  interest income, an approximate interest margin (labelled as approximate), bad
  loans where reported, deposits, and "Total income" in place of revenue. CASA
  and the credit-deposit ratio aren't in the statement tables, so the card says
  they're missing instead of guessing.

---

## 3.17 What I took away from this part

● The model was excellent at finding and quoting things. It was not reliable at
  judging them. The split that worked was: the model reads and quotes, Python
  verifies and decides, and a human checks a sample before anything ships.

● A hand check is worth more than any amount of prompt tuning. Seven wrong
  verdicts out of a small sample turned into seven general rules, and the ledger
  went from 4 of 7 to 8 of 8.

● Every time I had to choose between a feature that sounds impressive and one
  that is always right (dodged questions, quietly dropped, directional
  promises), I chose always right.

Next: Part 4, designing the app and the user experience.

