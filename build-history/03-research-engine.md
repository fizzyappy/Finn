# Part 3 · The research engine

[← Part 2](02-data-and-brief.md) · [Part 4 →](04-design-and-ux.md)

The pull side of FINN answers a different question: tell me about this company, and above all, does its
management keep its word? This part explains how the promise ledger works, how it was hand-checked and corrected,
and how the rest of the research page was designed so that the AI never gets the final say on a number.

---

## 3.1 What a research page needs to do

For any NSE company, the research engine produces one page in a fixed order:

1. FINN's take: one line that summarises the company's position.
2. The management report card: promises kept, questions answered, targets quietly dropped.
3. The promise ledger: every target management set, with its verdict.
4. Did they answer? Analyst questions and how management responded.
5. The numbers: snapshot, multi-year trajectory, balance sheet, cash quality, bank figures for lenders.
6. What the company sells: segments from the annual report.
7. Bull vs bear.
8. Sources: every document read.
9. Ask: a question box that answers only from these sources.

**Speed was designed in.** Statement tables need no AI and are published first, within seconds of a cold start;
transcript-based sections follow. Results are cached by company and the date of the newest source document, so a
company is only re-read when it files something new.

## 3.2 Reading transcripts properly

Every company formats its transcripts differently, so the engine works out who is speaking from the document
itself:

- speaker names are found from repeated "Name:" patterns and name-only lines;
- running page headers are only taken from page edges, so a frequent speaker is not mistaken for a header;
- roles come from the moderator's introductions, then the participant list, then behaviour (people who ask
  questions are analysts; people who answer are management).

Testing caught two real failures that shaped these rules: one company's CEO was first mistaken for a page header
because his name appeared so often, and a CFO was mistaken for an analyst. Both were fixed with general rules,
not by hard-coding those companies.

Quotes are checked word for word, but PDFs break words and lines in odd places ("gui dance"), so the check ignores
whitespace while requiring every other character to match, and it can find quotes that run across a page break.

## 3.3 The promise ledger

**How a promise is extracted.** Sentences that look like commitments (targets, guidance, "we expect", "by FY27")
are shortlisted by rules. The fast model then extracts each commitment in a fixed format: what is measured, the
target, the deadline, how firm the language is, the scope (whole company or a named segment), and the exact
quote. The quote is then checked against the transcript page.

**How the deadline is resolved.** Indian financial years run April to March, and management speaks loosely:
"this year", "H2", "next year", "by FY30", "FY24-25". A resolver turns each of these into a precise period, using
the date of the call (in an April–May call, "this year" means the new financial year).

**How a verdict is reached.** Python measures the target against the reported statements and decides:

- **Kept**, **Partly** (just short) or **Missed**, with the target, the actual figure and the period;
- **Too early** if the period has not been reported yet;
- **Quietly dropped** if management stopped mentioning it;
- **Not measurable** if the statements cannot answer it, with the reason.

The reason line is written by Python from the numbers. No model judgement is needed where a number exists.

## 3.4 The hand check that changed the design

Before trusting the ledger, I had the AI check it by hand on real companies: 45 statements from L&T and HAL.

| Check | First pass | After fixes |
|---|---|---|
| Extraction: genuine commitment, quoted word for word | 45 of 45 | 45 of 45 |
| Verdicts correct | 4 of 7 | 8 of 8 |

The verdict failures were the most valuable finding of the whole build. The main one: L&T's 8.5% margin guidance
was for its core engineering business, but it had been compared with the margin of the whole group, which
produced a wrong "Kept". Three general fixes came out of this:

- **Every promise carries a scope.** Only company-wide targets are judged against company-wide tables;
  segment targets are marked not measurable from the statements.
- **Constant-currency and US-dollar guidance is not converted.** IT companies often guide in constant currency;
  the statements report rupees, and converting would invent a number. These are marked not measurable.
- **A target far above what was achieved is not scored blindly.** If the actual is wildly above the target, the
  target almost certainly referred to a different scope or basis, so FINN says so instead of claiming success.

**"Quietly dropped" is a strong accusation**, so it needs strong evidence: the topic must go unmentioned for two
later calls before the deadline, and a metric discussed for a different period does not count as dropped. Related
metrics are grouped (operating margin and EBITDA margin count as the same topic), because managements label the
same target loosely.

## 3.5 Did they answer the question?

A judge reads each analyst question and the answer that followed, and labels it answered, partly answered or
dodged.

**The first version was too aggressive.** It flagged a request for clarification as a dodge. So the design was
tightened in two layers:

1. The model is instructed to flag only clear non-answers.
2. Python keeps a "dodged" label only if the quoted answer itself contains the evidence (an explicit refusal, a
   deflection), otherwise it is downgraded to "partly".

The result was checked by hand: on a sample of 15 labels, "dodged" was right every time it was used, and overall
agreement was 12 of 15, with every disagreement erring on the side of not accusing management. Later, every
"dodged" flag on one company was read by hand, and all four were explicit refusals to comment.

In the app, dodges are shown first; clarifications are hidden; and each question is shown next to the answer that
was given.

## 3.6 Analysis written by Python, phrased by AI

The risk with AI-written analysis is that it sounds confident while saying very little, or says something the
numbers do not support. The design keeps the reasoning in Python:

**FINN's take.** One line at the top of each company page, built entirely by Python from the facts already on
the page: promises kept, growth this quarter against its three-year trend, whether margins are widening or under
pressure, dodged questions, high debt, and whether profits turn into cash. Each part is coloured as good or bad
news.

**Bull vs bear.** Python first builds a numbered pool of facts, including comparison facts that a simple summary
would miss:

- revenue growth slowing or speeding up against its three-year average;
- profit growing faster or slower than revenue (margins widening or squeezed);
- a one-year revenue jump far above the company's normal growth, called out as "not like-for-like" only when
  per-share growth confirms that new shares were issued.

That last rule came from a finance review: HDFC Bank's three-year growth includes its merger, and FINN now says
so. The share-issue condition protects fast organic growers (such as Dixon) from being wrongly flagged.

The fast model then phrases at most three bull and three bear points, each citing fact numbers. Python discards any
point whose numbers do not appear in its cited facts, any point that uses praise words without an amount, and any
point that cites a fact marked for the other side.

**A sentence above every chart.** Each chart has one plain sentence computed by Python from its own numbers, for
example revenue growth, profit growth and margin change in the latest quarter.

## 3.7 The numbers section

- **Snapshot:** market cap, valuation, the latest quarter, returns on capital.
- **Trajectory:** seven years of revenue and profit, with margin, and the latest years highlighted.
- **Balance sheet:** debt, working capital and how many days cash is tied up.
- **Cash quality:** cash earned per rupee of profit each year, against a one-rupee line, because profit that never
  turns into cash is a warning sign.
- **Bank numbers for lenders:** net interest income and its growth, an approximate interest margin (labelled as
  an approximation), bad-loan ratios where the statements report them, and deposits. Measures the statements do
  not contain, such as the CASA ratio and the credit-deposit ratio, are listed as missing rather than guessed. For
  lenders, revenue is labelled total income, and cash-flow ratios are not treated as a quality signal.

## 3.8 What it sells: segments from the annual report

Annual reports are long, and some take minutes to download and read. The engine finds the segment table, has the
fast model read it, and checks the segment figures against reported revenue before marking them verified. Two
protections came from testing:

- very long documents skip the slow fallback text reader;
- reading an annual report has a four-minute budget, after which the page is published without segments and they
  appear on the next run.

A slow annual report once kept a finished run alive after a power cut, so the reader was moved to a background
thread that can never block the answer.

## 3.9 Ask about this company

The question box was designed so it cannot become a general chatbot that says anything:

- the model sees only a numbered evidence list built from the page: facts, ledger quotes, dodged questions,
  narrative points and segments;
- it must cite the evidence it uses;
- Python re-checks every number and praise word in the answer against the cited evidence;
- if the sources do not cover the question, it says so;
- suggested questions are generated from what the sources actually contain (deposits and loans for a bank, debt
  for a manufacturer).

## 3.10 Any company, live

A reviewer may test a company we did not choose, so live research for any NSE company was never cut. Twenty-five
companies are built into the app, including TCS, SBI, Bharti Airtel and ICICI Bank, which were researched ahead of
time so they open instantly. Anything else is read live by the research engine, with its progress shown in stages
and its position in the queue if another company is being read.

---

Next: [Part 4 · App design and user experience](04-design-and-ux.md)
