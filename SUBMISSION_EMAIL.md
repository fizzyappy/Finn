# Draft covering email (not sent)

**To:** assessment@enam.com
**Subject:** IIT Delhi – AI Engineer - 2027

---

Dear ENAM team,

Please find my submission for the AI Engineer build challenge: **FINN**, an app that tells an investor what their
holdings filed, which of those filings matter, and whether management keeps its word.

- **App (installable on a phone):** [VERCEL LINK]
- **Research engine (backend API):** https://finn-api-3des.onrender.com/health (free server: the first request after a
  quiet spell can take about 50 seconds)
- **Code, decisions log and evaluation:** https://github.com/fizzyappy/Finn
- **90-second demo path:** DEMO.md in the repository

What FINN does:
- **Push:** reads every exchange filing for a portfolio, ranks it (with a "why am I seeing this?" breakdown), and turns
  the few that matter into verified cards. Results numbers are read from the filing and checked by Python against a
  second source before they get a "verified" badge.
- **Pull:** for any NSE company, reads the last five earnings calls and the annual report and keeps a promise ledger:
  every target management set, measured against the reported numbers, with the exact quote and page. It also flags
  questions management dodged and answers questions only from verified sources.
- **Alerts:** price moves judged against each stock's own normal day, with a live 90-day backtest so the user can see
  how noisy a rule would be before turning it on.

How I worked: primary sources only; rules before the model; the model never does arithmetic; every quote is checked word
for word; every model call is cached and costed (the whole build used about 1 million tokens on Gemini's free tier,
USD 0). Evaluation results, including where FINN is still weak, are in the README and backend/spot_check.md.

Thank you for your time. I would be glad to walk you through it.

Best regards,
[YOUR FULL NAME]
[DEGREE, IIT DELHI, GRADUATING 2027]
[PHONE NUMBER]
[EMAIL ADDRESS]
