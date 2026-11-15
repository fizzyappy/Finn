# Part 5 · Deployment, fallbacks and final polish

[← Part 4](04-design-and-ux.md) · [Back to Part 1](01-research-and-plan.md)

A prototype that only runs on my laptop is not a product. This part covers how FINN was put online on free
infrastructure, how each predictable failure was given a fallback, how an outside review was triaged, and how the
AI's own mistakes were caught.

---

## 5.1 Deployment, step by step

Deployment was split between the AI and me. Anything involving my accounts, passwords, payment details or keys
was mine to do; the AI gave me exact click-by-click steps for each, and then tested the result itself.

**The research engine on Render.** The backend runs on Render's free plan. When Render asked for a card even on
the free plan, I chose to stay with Render and set it up myself rather than switch providers. The AI then tested
the live server end to end:

- health check and every data source;
- a company already in the built-in data (loaded from saved results in seconds);
- a company FINN had never seen (Tata Power), read live in about five minutes;
- the Ask box, answering with sources.

A small lesson came out of this step too: the AI had prepared an alternative host while I was still deciding,
without being asked. I had it removed, and the working rule became: offer options, wait for my choice, then build
only that.

**The app on Vercel.** The app is deployed from GitHub to Vercel and rebuilds automatically on every push. The
first deploy went out without its server setting; one setting and one redeploy fixed it. From then on, every
change in this build went live a minute or two after it was pushed.

**On my phone.** Before Vercel, I tried the app on my phone over the same Wi-Fi as my laptop. The campus network
kept devices apart, so the public Vercel link became the way to test on a phone from then on.

## 5.2 Fallbacks: designing for the ways free infrastructure fails

Free hosting fails in predictable ways. Each one was given a specific fallback.

| What can go wrong | What FINN does |
|---|---|
| The research server is asleep (free plan) | The app waits up to a minute, saying "waking up the free server", instead of failing |
| A source refuses a request on the day | The app ships with a snapshot of real outputs, so every built-in company and every brief still works |
| Another company is already being read | The app shows its place in the queue: "1 ahead of you · about 4 min" |
| One company's data fails during the daily refresh | That company keeps its previous cards, prices and research |
| Most companies fail during a refresh | The refresh stops and keeps the previous snapshot entirely |
| A restarted server has no memory | A small committed seed of cached answers is loaded, so finished work is never paid for twice |
| Strangers call the server and use up the free AI quota | Only the app may call the server, and each visitor is rate-limited per hour |
| The stronger model is overloaded | The router retries, falls back to the faster model, and labels which model answered |
| An annual report takes too long | The page is published without segments; they appear on the next run |

**Fresh data without my laptop.** A GitHub Action rebuilds the data every weekday after the market closes and
commits it, and Vercel redeploys automatically. Because it had never run, I triggered it once by hand; it ran
successfully from GitHub's servers and produced data matching the laptop's. A second scheduled job pings the
research server so it stays awake.

**Keeping cost figures honest.** A fresh cloud run starts with an empty usage log, which at one point reset the
displayed AI totals to just that run's calls. The totals now keep the larger figure, so they always reflect the
whole build.

## 5.3 Triaging an outside review

Near the end I used an independent, detailed critical review of the app: scores per area, a ranked list of issues,
screen-by-screen notes and risks. I asked the AI not to apply it blindly but to judge each point against what the
challenge actually asks for and what would make the app world-class.

The triage worked in three tiers:

1. **What a reviewer sees in the first minute:** an empty first screen, a contradictory quiet state, verified
   results hidden behind a custom date range, cluttered colour, developer words on screen. All fixed first.
2. **What the brief explicitly asks for:** announcement-type controls, percentage thresholds on alerts, a smarter
   bull/bear case, bank measures for lenders. Done next.
3. **What was too risky on the last day:** checking vague directional statements ("margins should improve").
   Doing it properly would have meant re-reading every call and adding verdicts nobody had checked by hand. A wrong
   "Missed" is worse than an empty one, so it was deliberately left for later and listed under "What's next".

The review also asked for two hand checks, which were done: every "dodged" flag on one company was read and
confirmed, and Reliance's unusually large one-day move was confirmed as a real, sustained move on heavy volume,
not a data error.

## 5.4 Seven upgrades in the final stretch

In the last stretch I gave the AI a prioritised list and asked for each item to go live as soon as it was done:

1. **FINN's take** at the top of every company page, built by Python.
2. **Four more companies pre-researched** (TCS, SBI, Bharti Airtel, ICICI Bank) so they open instantly. The free
   AI quota was watched throughout.
3. **A queue position** for companies being read live.
4. **Per-company safety in the daily refresh.**
5. **Chart labels and tap-to-read values,** and earnings calls named by quarter.
6. **Directional promises:** analysed and deliberately postponed, as explained above.
7. **Bank numbers for lenders.**

Each was built, tested and pushed separately, so a problem in one could never hold up the others.

## 5.5 How every change was verified

- **119 offline tests** on real captured responses and recorded model answers, run after every backend change.
- **Automated screen checks:** a headless browser opened 20 screens and states at phone size after almost every
  change, saved screenshots and checked for console errors, accessibility problems, colour contrast and horizontal
  overflow.
- **Secret scans** before every commit, so the API key could never be pushed.
- **Live checks after deployment** of the server, the app and the daily refresh.

## 5.6 When the AI got it wrong

The value of working this way showed in the mistakes that were caught before a reviewer could see them:

| Mistake | How it was caught | The fix |
|---|---|---|
| Judged a segment's margin target against the group's margin | hand check | every promise carries its scope |
| Called a reaffirmed credit rating an upgrade | summary checks | action words must appear in the filing |
| Mistook a CEO for a page header and a CFO for an analyst | live runs | roles from introductions and question-and-answer behaviour |
| Treated a clarification as a dodged question | hand check | a stricter judge plus a Python evidence rule |
| Listed a neutral count as a bull point | outside review | Python comparison facts, each tied to a side |
| A test that reached the live model once a working key was present | test run | tests forced to run offline |
| Built an alternative host I had not asked for | my review | removed; options are proposed, not built |
| Reported a clean screen check from a run that had stopped halfway | its own follow-up check | the test was fixed and every check re-run, and I was told plainly |

The last row matters most. The AI was expected to report its own mistakes as soon as it found them, and it did.

## 5.7 What the build used

- **Claude Code:** the engineering agent for planning, code, live runs, tests, screen checks, commits and
  deployment checks, reporting in plain language after every step.
- **Gemini in the app:** about 400 model calls and one million tokens across the whole build, with roughly two
  thirds of requests answered from cache. Total cost on the free tier: USD 0.
- **Free hosting:** Vercel, Render and GitHub Actions.

## 5.8 What is left for later

- push notifications for headline cards and alerts (the service worker is already in place);
- checking directional promises by whether the metric moved the right way;
- sector measures from annual reports, such as interest margin and bad loans for every bank;
- a larger blind evaluation of the classifier and the dodged-question judge;
- for a real launch: licensed real-time exchange feeds, importing holdings from a broker statement, accounts and
  sync, paid hosting without cold starts, and a check of SEBI's research-analyst rules.

---

[Back to Part 1](01-research-and-plan.md)
