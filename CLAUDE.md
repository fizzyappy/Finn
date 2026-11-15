# FINN — project rules

FINN is the build for the ENAM AI Engineer Build Challenge. These rules apply to every change in this repo.

## Data and research
- **Primary sources only.** Research facts come from the original source: exchange filings (BSE/NSE), company annual reports, investor presentations, concall transcripts, regulator documents. No blogs, news rewrites or aggregator opinions as evidence.
- **Every quote is verified verbatim against its source.** A quote shown to the user must match the source text exactly; store the source URL/document and location with it. If it cannot be verified, it is not shown.

## Code
- **No company-specific code.** Logic is generic and driven by data/config. No `if ticker == "XYZ"` branches, no hard-coded per-company rules.
- **Rules before LLM.** If a deterministic rule, parser or lookup can do the job, use it. The LLM is used only where rules cannot do the work.
- **The LLM never does arithmetic.** All numbers, ratios, growth rates and comparisons are computed in Python. The LLM may only describe numbers that Python has already computed and passed in.

## LLM usage
- **Provider: Google Gemini (free tier).**
- **All LLM calls go through one router module.** No direct SDK calls anywhere else in the codebase.
- **Cache every LLM call by content hash** (hash of model + prompt + inputs). A repeated call returns the cached result instead of calling the API.

## Secrets
- **Never commit secrets.** API keys live in `.env` (git-ignored). `.env.example` lists the variable names with empty values.

## Housekeeping
- Record notable choices in `DECISIONS.md` (Decision | Why | What we gave up).
- Track progress against `PLAN.md`.
