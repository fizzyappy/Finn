# FINN app (React + Vite + TypeScript, installable PWA)

Four screens, phone-first (390 px), centred column on desktop:

| Screen | What it does |
|---|---|
| **Brief** | What your holdings filed, ranked. Progress ring, window chips (since last look / 24h / 3d / 7d / custom 14d), hero cards (results with verified badge and checks, people with sourced career lines, others with headline + one-liner), market-reaction chip, swipe right to clear, swipe left for less like this, tap "Why?" or long-press to flip to the score breakdown, one-liners, unusual moves, collapsed categories, quiet-day and "You're clear" states, read aloud. |
| **Research** | Search any NSE company (autocomplete). Management report card, promise ledger (verdict badges; tap for the verbatim quote with page link, revision trail and target-vs-actual chart), dodged questions, story vs numbers, snapshot, trajectory, balance sheet, cash quality, segments, bull vs bear, sources. Cold start for new companies shows staged progress with tables first (needs the backend). |
| **Alerts** | The rule as a sentence with tappable values, sliders, a live 90-day backtest strip ("about N a week"), recent alerts with filings made before each move. |
| **Settings** | Cost meter, portfolio weights, swipe tuning (reset), data as-of and per-source status, backend URL, "How FINN thinks". |

## Data

`public/data/` is a frozen snapshot of real outputs, made by `python -m finn.export_snapshot`
in `backend/`. The app always works from it. If a backend URL is set in Settings, research for
companies outside the snapshot runs live.

## Run

```bash
npm install
npm run dev              # http://localhost:5173
npm run build            # type-check + production build to dist/
node scripts/screenshots.mjs   # screenshots of every screen/state + console errors + axe + PWA checks
```

Screenshots: `screenshots/` (`report.json` holds the console errors, accessibility and PWA results).
