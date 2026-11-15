# Build history

FINN was built with Claude Code over 13–15 November 2026, task by task (see `PLAN.md`), with
every choice and its trade-off logged in `DECISIONS.md` and every step committed to git
(`git log` shows the full sequence, one commit per milestone).

| Phase | Where to look |
|---|---|
| 1. Setup, tool check, rules | `CLAUDE.md`, `PLAN.md`, first commit |
| 2. Data pipes, proven live | `backend/validation_report.md` |
| 3. Push engine | `backend/push_report.md` |
| 4. Pull engine + hand spot-check | `backend/research_report.md`, `backend/spot_check.md` |
| 5. App | `frontend/`, `frontend/screenshots/` |
| Decisions throughout | `DECISIONS.md` |

**Start here:** [`BUILD_LOG.md`](BUILD_LOG.md), a readable account of how the author and Claude Code built FINN:
phases, turning points, what the AI got wrong and how it was caught.

## Session transcripts

The raw Claude conversations (exported by the author, with API keys removed) are in this folder.
