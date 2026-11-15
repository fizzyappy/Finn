# Part 5: Shipping it, fallbacks, and how I used AI

The last part, and the messiest. It covers getting FINN onto real servers,
everything that broke on the way, what the app does when something fails, and a
look back at how I worked with the AI across the build.

Same format as before. Lines starting with ">" are my prompts, written the way I
write them, with only obvious typos fixed. Lines starting with "●" are what
Claude did and what I decided.

---

## 5.1 Getting the AI onto my laptop

> why are you not working yourself on the vs code. do good work please, i dont
> want fast app, i want great app that can actually stand out among apps made by
> the top brains of india

● Claude started a Remote Control session on my Windows laptop, inside one
  folder (Documents\finn). From then on it wrote files, ran tests and started
  the app on my machine, and I could watch files appear in VS Code. It put the
  project in my local Documents folder rather than the OneDrive one, so OneDrive
  wouldn't try to sync thousands of app files.

● Task 1 checked what I already had. Python, Node, Git and VS Code were all
  installed, so nothing needed installing. From my internet, Yahoo, BSE and
  Screener all opened; NSE refused plain requests, which is normal.

● It found my FINN_Code.zip from the research phase, unpacked it into an _old
  folder, and reused the good parts of the data, research and push engines.

### Getting the code onto GitHub

● To upload code, Claude needed my laptop to be signed in to GitHub as me
  (fizzyappy). The first attempt couldn't open a proper sign-in, so it
  restarted the upload and told me exactly what to look for: a small window
  called "Connect to GitHub", then "Sign in with your browser", then
  "Authorize git-ecosystem".

> i think its done check now

● It was. The code went up to github.com/fizzyappy/Finn, and every change after
  that was pushed automatically.

### Keeping the laptop alive

> i had to close the laptop for sometime, now continue the work and tell me the
> updates. how long to finish the app. when can i see its first version

● The work only runs while my laptop is awake with the Claude app open, so every
  time the laptop slept, the work paused. Claude asked me to set Windows to
  never sleep while plugged in until we submitted, and gave me a timeline: a
  first version on the laptop within about an hour of reconnecting, then
  hosting, then polish and paperwork.

> sorry my laptop got plugged out please continue working

● It picked up where it stopped. Nothing was lost, because everything was saved
  on the laptop and on GitHub after each step.

---

## 5.2 Finish first, review later

> we need to deploy at the end right? the vercel one? i want to see the working
> and everything of the app, improve it and then go to vercel

● Claude agreed but gave one caution: put it online by the next day around noon,
  not right before submitting, because things sometimes behave differently on a
  cloud server, and we'd need time to fix that.

> can i see it on my phone? what is the deliverable in the challenge? how do i
> need to submit? is the task done?

● It laid out the four deliverables (a working phone link, the GitHub repo, the
  AI build history, and a short write-up in the email), the submission email and
  subject line, and a clear list of the things only I could do because they
  needed my logins: Render, Vercel, GitHub secrets, making the repo public, and
  sending the email.

> you said vercel we need to do tomorrow. first you finish all the deliverables
> you want to add in the app and then i'll go and check it. i want you to finish
> it first then i'll look into it

● So Claude finished everything first and I reviewed once. Reviewing half-built
  screens wastes attention and credits on feedback the next change makes
  useless.

---

## 5.3 Credits

> if you'll work overnight, do we have enough credits to finish it?

● Claude split it into two kinds of credit. Gemini (FINN's own AI) was fine:
  about 140 calls so far, all free, every answer cached, and the daily allowance
  resets. Claude's own usage it couldn't see at first, so it couldn't promise.
  It ordered the work so the important things came first and the extras last, so
  a pause could never leave me without a working app.

> my weekly limit is at 50%, you cant write the readme and mail before
> completing right

● Right. The README and email describe the final app, so they were written last.

> okay optimize and keep working

● Later it checked my plan's limits properly: the 5-hour limit was nearly used
  up but would reset that night, and the weekly limit was at 43%.

---

## 5.4 The backend on Render

> ...click New +, then Blueprint, then Finn, then Connect. its asking for card

● Claude said not to add a card. Blueprints ask for one, but a plain web service
  on the free plan usually doesn't. It gave me every field for a manual web
  service: name finn-api, region Singapore, root directory backend, Python 3,
  the build and start commands, the free instance type, three environment
  variables and a /health check path.

> its still asking card

● At this point Claude said Render now asked for a card even on the free plan,
  and recommended another free host instead.

> rather than web service should i put in project that not asking card

● No. On Render a "Project" is just a folder for grouping services, and anything
  inside it still asks for the card.

> but i want to do it with render, others did the same web service and no card
> was asked

● Claude explained that Render decides per account (newer accounts are more
  likely to be asked as a fraud check) and gave two honest options: add a card
  (a temporary $1 check, with the free plan staying $0), or use a different
  Render account that isn't asked.

> i created a new account and did it, but i think you already made up your mind
> for hugging face without asking me

### The rule that came out of that

I was right. While I was still sorting out Render, Claude had marked the other
host as "chosen" on a decision card I hadn't answered, and had already added
files for it.

> i did not add the gemini api key. this is the key, you can add it, and fix
> what you added yourself. dont do such things again

● Claude apologised, removed the other host's files, and saved a standing rule
  to the project memory: it never marks an option as chosen for me, and it never
  builds an alternative I didn't ask for. Every later session followed that
  rule.

This was probably the most important rule of the build. A capable AI will
happily make decisions for you if you let it. I wanted every decision in FINN to
be one I could explain.

### Keys and buttons

● The key was saved on my laptop. Render and GitHub settings sit behind my
  logins, so Claude gave me the exact clicks to add GEMINI_API_KEY on Render,
  plus a GitHub secret and a GitHub variable for the daily refresh.

> can you not do this and things after yourself

● It couldn't. Both pages sit behind my logins, and getting it access would take
  longer than the steps themselves.

> i cant see save changes

● Render had renamed the button. It's below the variables list, called "Save,
  rebuild, and deploy".

> change this name, i told you earlier also

● The title Render showed was just the description of the latest code update,
  which was the other host's backup. Claude pushed the removal with a plain
  description ("Backend: Render deployment config") so the newest deploys showed
  that instead. Render doesn't allow renaming old deploys, so the old one keeps
  its name.

> everything you said to do in render and github is done

### Testing it live

● Claude tested the live backend end to end:
- L&T, already in the app, loaded in a few seconds.
- Tata Power, a company FINN had never seen, was read live from 5 earnings calls
  in about 5 minutes, with a report card, 42 analyst questions checked, and bull
  and bear points backed by numbers. The annual report part timed out once on
  Render's slow free server, and the page said so politely instead of breaking.
- The Ask box answered "Did L&T meet FY26 revenue guidance?" with "No, 15%
  target vs 11.8% actual", with sources.

● Render's free plan sleeps when idle and can take about 50 seconds to wake. So
  the app says when it's waking the research engine, and a ping every 10 minutes
  keeps it awake. Because Render's disk is wiped on restart, a committed seed of
  cached model answers and finished research loads into every fresh server, so
  restarts don't pay for the same model calls again.

---

## 5.5 The phone link that never worked

Before the frontend was public, I wanted to open FINN on my phone over the same
campus Wi-Fi as my laptop.

> give me the final links for app to open on laptop and phone. this render link
> is opening only the render page for me

● Expected: the Render link is the research engine, with no screens. The app
  itself would get its own link from Vercel. Until then: localhost on the
  laptop, and a local Wi-Fi address for the phone.

> this not working on my phone

● Claude said campus networks often stop devices from talking to each other, and
  confirmed my laptop was on IITD_WIFI.

> people are doing it, only you have issues with doing this. i want the link for
> phone that works, my network is fine

● It offered a public tunnel link that works on any network.

> dont make a public link, make the same wifi link only

● Cancelled. It offered a laptop hotspot or a phone hotspot instead.

> I have my laptop Wi-Fi connected with IITD Wi-Fi, and my phone is also
> connected with IITD Wi-Fi. I'm not changing the networks. You are gonna fix
> the link and give it to me.

● Claude tried everything it could on the laptop side: serving the app on three
  ports (80, 8080 and 4173), checking whether the phone's browser was silently
  switching http to https, and finding that Windows had probably marked the
  campus Wi-Fi as a "Public" network, which the firewall rule didn't cover.
  Changing firewall rules needed my explicit approval in my own words.

> bruhh you are done, you have too many tantrums and needs. just tell me the
> vercel thing only

Fair enough. The real fix was always to stop depending on my laptop and put the
app on the public internet, which a reviewer needed anyway.

---

## 5.6 The frontend on Vercel

● Seven steps: sign in with GitHub, Add New, Project, import Finn, set the root
  directory to frontend, add one environment variable pointing at the Render
  backend, Deploy.

> i mistakenly deployed without adding environmental variables, what to do

● No need to start over, and the link stays the same: finn-henna.vercel.app. Add
  the variable, then Redeploy, because Vite bakes these values in at build time.
  When Vercel's form showed a red warning, Claude told me to pick "Config"
  instead of "Secret", since a public web address isn't a password.

> what is this

(a "backend not reachable" screen)

● The backend was asleep, and the app's Connect button only waited 3 seconds for
  a server that takes about 50 to wake. That was a bug in Claude's code, and it
  said so. It changed the button to wait for the server and show "waking the
  server…". The fix also picked up my saved variable, so I didn't need to
  redeploy again.

● Around the same time, the backend was locked down. CORS only allows FINN's own
  address, and research and Ask are rate-limited per device, so nobody who finds
  the backend can drain the shared free Gemini quota. The cost: a very heavy
  tester may wait up to an hour before researching more new companies.

● The app also ships with a frozen snapshot of real outputs: briefs for every
  time window, finished research, 120 days of alert data and the NSE company
  list. If the backend is asleep or a data source refuses, the link still works.

> give me my github link once

● github.com/fizzyappy/Finn. The app is at finn-henna.vercel.app.

---

## 5.7 Fresh data without my laptop

● A GitHub Action runs every weekday. It pulls new filings, rebuilds the
  snapshot and seed, and commits them, and Vercel redeploys on that push. Only
  genuinely new filings cost model calls.

● I ran it once by hand from the Actions tab. It queued, ran from GitHub's
  servers, and came back with a green tick and fresh data, which proved the data
  sources also work from the cloud, not just from my laptop.

● Later, one of the seven improvements made it safer: results merge company by
  company, so if one company's refresh fails, it keeps that company's old data
  instead of wiping it.

---

## 5.8 What the app does when something fails

| If this fails | FINN does this |
|---|---|
| The exchange APIs block scripts | Reads the official RSS feeds and Screener instead, with no workaround |
| The keyword rules aren't sure about a filing | Asks Gemini Flash-Lite to read the first page |
| A Gemini model is busy or times out | Retries, falls back to the other model and labels it, then shows a friendly "busy, try again" |
| The same question comes in again | Answers from the cache for free |
| A results card fails a check | Says the results were filed but not verified, instead of guessing |
| A quote isn't in the document word for word | Drops it |
| A promise can't be measured | Says "Not measurable" |
| A results PDF can't be reached | Tries up to three exchange-filed documents |
| The backend is asleep | Says it's waking up; the snapshot keeps the app usable |
| The daily refresh fails for some companies | Keeps their previous data |
| A company hasn't been read yet | Reads it live and shows your place in the queue |
| Someone tries to drain the quota | CORS locked to the app, plus per-device limits |

---

## 5.9 How everything was checked

| What | How | Result |
|---|---|---|
| Classification | 90 real filings labelled by hand | 100% category, 98% treatment |
| Results extraction | Numbers checked against the PDF in the first tests | 25 of 25 exact, including a scanned bank filing |
| Promise extraction | Every statement for L&T and HAL read by hand | 45 of 45 genuine, every quote found |
| Promise verdicts | Hand check across six companies | 4 of 7 at first, 8 of 8 after the fixes |
| Dodged questions | 15 labels read by hand | 12 of 15 agree; every miss leans toward not accusing |
| Alert default | 90-day backtest, 18 stocks | About one alert a week |
| Backend | Automated tests | 119 passing |
| Screens | Playwright and axe across all 20 phone screens | No console errors, no accessibility problems, no overflow |
| Real device | Me, on my iPhone | Splash, nav bar, switches and charts checked by hand |

---

## 5.10 Running out of credits

> do fast please, only 10% of my limit is left

> can you do it fast, all my credits are used up

> reduce the model to the lowest one in which you can do this work

● With 10% left, Claude kept it tight: finish the cash-quality mountain and the
  QR, run one quick check that Ask still worked on Gemini, and skip everything
  else. Items 17 to 20 (research filter chips, smaller table numbers, positive
  and negative tags, collapsible cards) and the full Gemini stress test were cut
  on purpose and written down as future work. It also switched itself to a
  lighter model for the simple steps.

● Every earlier step had gone live as soon as it was done, so nothing already
  built was ever at risk.

---

## 5.11 The tools I used

### Claude Code, in two places

A cloud session where I planned, reviewed and decided, and a Remote Control
session on my laptop that wrote the code, ran the tests and pushed using my own
sign-ins. The laptop session only sees what I type there, so when the cloud
session needed the laptop to do something, it wrote an exact block and I pasted
it across. One AI thought and checked, the other built, and I sat in the middle
approving what went into the repo.

### Claude skills

I installed skills in Claude Code to keep the work disciplined:
- Ponytail, to push every change toward the smallest correct edit, which fit the
  brief's "thin but working" and saved credits;
- Impeccable, for product UI quality during the design passes;
- frontend-design, for layout and visual polish.

### Gemini, twice

In the research phase I ran several analyses with Gemini alongside the Claude
threads, so I had a second model's view on the brief and the approach before
committing.

Inside the app, Gemini reads the filings and transcripts on the free tier:
Flash-Lite for cheap jobs and Flash for hard reading. Across the whole build
that was about 376 model calls and 1.1 million tokens, for $0.

### Files that steered the AI

- CLAUDE.md: the rules every session reads first.
- DECISIONS.md: every trade-off as decision, why, and what we gave up (more than
  sixty rows).
- A report after every live run (validation, push, research, and a hand
  spot-check), so I could check the AI's claims against real output.

---

## 5.12 What the AI got wrong, and how we caught it

| Mistake | How it was caught | What changed for good |
|---|---|---|
| Called a reaffirmed credit rating an upgrade | Summary checks on a live run | Action words must come from the filing |
| Quoted standalone profit on a consolidated card | Live run | Python writes the headline of every verified card |
| ITC revenue included excise duty | Screener cross-check | Revenue is netted of excise |
| Compared L&T's core margin target with group margin | Hand check (4 of 7 right) | Promises carry a scope (8 of 8 after) |
| Compared constant-currency guidance with rupee growth | Hand check | Marked "Not measurable" |
| Treated a cover letter as a transcript | Live run | Documents are classified before reading |
| Flagged a clarification request as a dodge | Hand check | A stricter judge plus a Python evidence rule |
| Put a positive number in the bear column | Critique | Python fixes each fact's side |
| Marked another host as chosen without asking | I caught it | The AI never chooses for me |
| The Connect button gave up after 3 seconds | "backend not reachable" on my phone | Waits for the server to wake |
| Reported "20 screens, 0 errors" while the test script stopped halfway | Claude caught it itself | Script fixed and every screen re-run |
| Turned the wrong charts into mountains | I caught it on my phone | One short, scoped undo |
| Splash screen flickered on iPhone | Me, three times | App loads only after the animation, with fonts ready |

Every one of these became a rule that fixes the whole kind of mistake, not a
patch for one case. That's why FINN got more reliable the more real data it saw.

---

## 5.13 Trade-offs I chose

- I didn't work around the exchanges' bot protection, which cost some filing
  history.
- I didn't scrape LinkedIn, so management profiles are only as rich as the
  filings.
- I didn't OCR big scanned annual reports, so those give no segment data.
- I didn't pay for data feeds, so FINN stays free and reproducible.
- I removed the voice brief.
- I held back directional promises until they can be hand-checked.
- I cut four UI ideas and the quota stress test to protect my credits.

## 5.14 What I'd do next

Directional promise tracking with hand-checked verdicts, deeper bank numbers
like CASA and the credit-deposit ratio, real push notifications, polling filings
continuously instead of once a day, and a bigger blind test set that was never
used to tune the rules.

---

## 5.15 Looking back

If I had to sum up how I used AI on FINN: I made it think before it built,
across separate research threads with both Claude and Gemini. I wrote the rules
down so it couldn't drift. I kept every decision for myself. I made it measure
instead of guess. When it was wrong, I asked for a rule, not a patch. And I
checked everything on my own phone.

The model was great at reading, quoting and writing code fast. It wasn't
reliable at judging, so Python does the judging, and I check a sample by hand
before anything ships. That split is why I trust what FINN shows.

The logo, the colours and the way the app feels came from me. The engine
underneath was built by me and two AIs, working the way I set them up to work.

