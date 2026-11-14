# Promise ledger: hand spot-check (14 Nov 2026)

I read every statement the engine extracted for **L&T** (20 statements, 5 calls) and **HAL**
(25 statements, 5 calls) against the transcript pages, then checked every scored verdict
across all six companies.

## What the engine got right first time

- **Extraction precision: 45 of 45.** Every extracted item was a genuine forward-looking
  statement by management (not an analyst, not the past), and every quote was found word for
  word on the page cited.

## What the first pass got wrong, and the generic fix

| # | Company | Error | Fix (no company-specific code) |
|---|---|---|---|
| 1 | L&T | 8.5% margin target for the core Projects & Manufacturing business compared with group margin → wrongly **Kept** | Promises carry a scope; only company-wide targets are measured. Same target labelled "company" in one call and by segment in another takes the segment's scope |
| 2 | L&T | Same margin target restated under another label ("EBITDA" vs "EBIT") → wrongly **Quietly dropped** | Margin types form one family for the drop check |
| 3 | HAL | "FY24-25", "'26-'27" read as the first year (3 wrong horizons) | A fiscal range names the year it ends in; with several years named, the last one |
| 4 | HAL | Company 10–11% FY25 target merged with a repair-business 9–10% target → recorded as a "cut", never scored | Company-wide and segment targets are separate trails |
| 5 | HAL | Later "double-digit growth" (no number) erased the earlier "10% to 11%" | Verdict uses the latest statement that has a number |
| 6 | Infosys | 3–3.5% revenue guidance is in constant currency (said in the sentence, not in the model's short quote) → wrongly **Kept** vs INR growth | The full source sentence is checked for constant currency / USD |
| 7 | Titan | 13–14% target vs 44.9% actual → wrongly **Kept** (target was for a narrower scope) | An actual far above the target is not scored and is flagged as a likely scope mismatch |

First-pass verdict precision on the scored L&T + HAL items: **4 of 7 correct**.
After the fixes: **8 of 8 scored verdicts across the six companies match my reading** of the
transcripts and the tables (the fixes are general rules, so this is now in-sample).

## Still imperfect

- Scope labels come from the model and can be wrong (L&T's 2% credit-cost target is for its
  finance subsidiary but is labelled company-wide; it is not scored because credit cost is not in
  the tables).
- Dodged-question labels: of the two "dodged" labels in this run, Infosys's (a security-breach
  question answered with "I do not have any specific comments on it right now") is right; HAL's
  is really a request to repeat the question, not a dodge. 1 of 2 correct.
- Many statements are "Not measurable" from the tables (order inflow, segment targets, constant
  currency, no date). That is shown as such rather than guessed.
- No target in this run survived the rules as **Quietly dropped**; the one the first pass found
  was a false alarm (error 2 above).
