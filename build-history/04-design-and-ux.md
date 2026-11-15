# Part 4 · App design and user experience

[← Part 3](03-research-engine.md) · [Part 5 →](05-deploy-and-polish.md)

The engine could be perfect and still fail if the app felt like a dashboard of numbers. This part explains how
the interface was designed, how I directed it through repeated review on my phone, and the reasoning behind each
change. FINN's logo and identity are my own design, and the app's colours come from the logo.

---

## 4.1 Design principles

Before any screen was drawn, the design goals were set from the same analysis as the engine:

- **Phone first.** An investor checks their portfolio on a phone, in a minute, between other things. Every screen
  is designed for one hand and a small screen, and the app installs to the home screen like a native app.
- **Calm, not alarming.** Most days nothing important happens. The app should say so confidently instead of
  filling the screen to look busy.
- **Every element answers "so what?".** If a number or a card does not help the investor decide whether to pay
  attention, it does not belong on the screen.
- **Trust must be visible.** Verified badges that open into their checks, "Why?" on every card, quotes with page
  links, and plain statements when something is not known.
- **Premium means restraint.** Clean spacing, few colours, consistent formats, smooth motion, nothing flashy.

## 4.2 The four screens

- **Brief:** what your holdings filed, ranked by how much it matters.
- **Research:** does management keep its word, with the quote and page.
- **Alerts:** price moves that are unusual for that stock, tested on 90 days of history.
- **Settings:** your portfolio, which announcement types reach you, and what FINN costs to run.

## 4.3 How the design process worked

The design was shaped in short loops. I opened every new version on my phone, used it as an investor would, and
told the AI exactly what felt wrong: crowded, clumsy, tacky, too bulky, hard to navigate, not premium, too bouncy,
not clickable. The AI translated each reaction into a specific design change, implemented it, re-ran the
automated checks on every screen, and sent me a screenshot. Nothing shipped until it passed both my review and the
automated checks (no console errors, no accessibility problems, no contrast failures, no horizontal overflow).

The rest of this part follows the main decisions that came out of those loops.

## 4.4 Identity: logo, wordmark and opening

**The logo.** I drew the F by hand first, then refined it with AI in Illustrator. Every part of it carries an idea.

- *The upper arm* is long and extended. It stands for everything an investor is exposed to: announcements, annual
  reports, earnings calls, market moves, management guidance. It is the breadth of what comes into FINN.
- *The middle arm* is shorter on purpose. FINN does not pass on everything it receives; it narrows it down to what
  deserves attention. Read the two arms together and they are also the core comparison FINN makes: the upper arm is
  what management said, the middle arm is what the numbers show.
- *The gap between them* keeps the F from looking like two decorative ribbons. It is the line between information
  that exists and information that deserves your time, which is the problem FINN solves.
- *The slant* is a style choice first. It also gives a horizontal letter forward motion, and FINN watches what
  changes rather than storing the past. The curves make the letter one continuous form, like raw information being
  turned into something useful. No angle stands for a calculation.
- *The colours:* mint green for clarity and the signals that matter, a darker green for depth, a lighter top surface
  for incoming information, a soft inner shadow for separation, and a deep forest background for seriousness.

The app's colour scheme comes straight from the logo. The AI redrew the mark as a vector so it stays sharp at every
size, built the app icons from it, and renamed the files so phones holding an old cached icon would load the new one.

**The wordmark.** I asked for the "FINN" letters to be thinner; they were set in a lighter weight with wider
spacing, which reads as calmer and more premium.

**The opening animation.** I wanted the logo to form when the app opens, for two to three seconds. The F's two
bars slide in one after the other, then the wordmark and a short tagline appear, and everything fades into the
app. It plays once per visit and can be skipped with a tap.

When it flickered on my iPhone, the AI looked for the real cause rather than adjusting timings. There were three:
the app was loading underneath the animation, and an animated layer over blurred glass panels flickers in iPhone
Safari; the font swapped partway through; and Safari moves parts inside an SVG unreliably. The fix was structural:
the animation now plays on its own, waits for the fonts, moves each bar as its own element, and only then does
the app fade in.

## 4.5 Colour

The first theme used a bright mint green on a green-tinted dark background. On review, I felt the neon green looked
tacky, and that good apps use a plain background. The AI agreed with the reasoning: in finance, green carries
meaning (gains, good news), and when everything is green, real gains stop standing out.

The result:

- a plain near-black background, with only a faint tint near the logo;
- one calmer sage-mint accent instead of neon, used for the main action, selection and good news;
- a softer red for falling numbers;
- gold for margins and secondary lines.

At one point a review recommended removing most of the colour and glow entirely. When I saw it, the app had lost
the look I liked, so I asked for the original look back with the new content kept. That back-and-forth is part of
the process: the review informed the decision, but the final look was my call.

## 4.6 The Brief screen

**The empty-screen problem.** On a quiet day the first version opened on "0 filings · 0 matter", which is the
worst possible first impression for a product whose promise is "we show you what matters". It went through
several versions:

1. A big "quiet" card, which was calm but empty.
2. Falling forward to the shortest time window that has something, which worked but put zeros next to cards.
3. The final design: a slim "Today: nothing new" line under the title, then a clearly labelled "Earlier this
   week" section with the week's cards.

**The header.** I found the first header clumsy (a two-line title, a sub-line, a tip box and a large button
stacked together), so it was rebuilt: a progress ring showing how many cards are left to clear, a short title, a
thin filter funnel ("20 filings → 3 worth knowing → 1 need you") and a one-line portfolio pulse (how many holdings
beat the Nifty this week, and the biggest move).

**Time windows.** Since last look, 24 hours, 3 days, 7 days and a custom date range. Windows with nothing that
needs attention are hidden, so the chips are never a list of empty options. The custom picker was rebuilt so the
date boxes fit the card on a phone and dates read as "1 Nov 2026".

**Cards.** Each card shows the company in a highlighted chip (tap it to open the company's research), how large
the holding is ("your 6% holding"), the market's reaction, the filing link, Why? and a visible Done button.
Swiping right still clears a card; swiping left means "less like this". Verified results are pinned in their own
"Latest results" section so they are never hidden behind a time window. Results that cannot be verified say so
in the headline.

**Removed: reading the brief aloud.** The app once read the important cards aloud using the phone's built-in
voice. I found it mechanical and over-engineered, so it was removed. Not every feature earns its place.

## 4.7 The Research screen

- **The landing page** lists "Your holdings" first and "Other companies" second, each with a clear verdict
  (promises kept, questions dodged, targets tracked) and when the next target is due. The long explainer was cut
  to one line.
- **Company pages** open with FINN's take, then the report card (with zero tiles greyed out, and "questions
  answered" instead of the more accusatory "dodged"), then a sticky jump bar to Promises, Answers, Numbers,
  Bull/bear, Sources and Ask. A back link returns to the list.
- **The Ask box** sits at the end of the page, with a full-size button and suggestions that wrap rather than being
  cut off.
- **Names never overflow:** long company names are shortened cleanly, and pills sit in their own column.

## 4.8 The Alerts screen

- **Recent alerts first,** then the rule you can change, then what the rule would have done over 90 days.
- **The rule reads as a sentence:** "Tell me when any holding moves more than 3.0× its usual daily move with
  volume above 2.5× average." The values are tappable. When the value boxes touched each other on a phone, the
  sentence was made smaller with more line spacing.
- **The slider shows real percentages,** for example the equivalent move for the most and least volatile
  holdings, because "3×" alone means little.
- **The backtest strip shows alert days as peaks:** each bar rises to the size of that day's biggest move, with a
  small glowing white tip and a green glow, so the most significant days stand tallest.
- **The verdict changes with the count:** "getting noisy", "a sensible level", "selective" or "very quiet".

## 4.9 The Settings screen

- **Announcement types:** Mute, Normal or Boost for each type of filing, on a sliding toggle. I found the first
  version did not look clickable, so it became a recessed track with a raised thumb. Mute, Normal and Boost each got
  their own colour (soft red, grey, green), and the slide was tuned from bouncy, to smooth, to a gentle settle.
- **Cost:** a cost meter first sat at the top of Settings. I questioned whether it was even needed. It stayed
  because the challenge rewards cost awareness, but it moved to a small "What it costs to run" line at the bottom.
- **Developer settings** (the research server address) are tucked away, because a consumer app should never ask
  for a server address.

## 4.10 Navigation and motion

I found the app hard to navigate and asked for smooth, app-like movement. The changes:

- every tab in the bottom bar shows its name, not just the selected one;
- screens slide in the direction you move along the bar;
- section titles ease in as you scroll; jumps scroll smoothly;
- buttons, chips and rows respond to a press;
- the bottom bar was made slimmer when it felt bulky, then given a raised, three-dimensional look when it got lost
  against the page.

## 4.11 Charts

Charts went through the most iteration, because they are where an app looks either premium or cheap.

- **Revenue and profit:** bar charts with older years in grey and the latest two years highlighted, the first and
  last values labelled, rounded tops, a gentle grow-in, and values on tap. Margin is drawn as a line on top.
- **Cash quality:** the one mountain chart, by my choice: a green filled area of cash earned per rupee of profit,
  drawn from the real yearly points with jagged peaks, small glowing white dots on each peak, and a dashed line at
  one rupee.
- **Promise targets:** a band showing the promised range, with the actual result sliding in, green if met and red
  if missed.
- **A sentence above every chart** says what the chart shows in plain words, computed by Python.

Along the way other chart styles were tried, including mountain charts for revenue, profit and price. I decided
only cash quality should be a mountain, and everything else was returned to its clearer form.

## 4.12 Copy and formats

Small inconsistencies make an app look unfinished, so they were standardised:

- the rupee sign everywhere, and Indian number grouping;
- dates as "12 Nov 2026" and quarters as "Q2 FY27";
- calls named by quarter instead of by date;
- no developer words on screen ("snapshot", "API", internal field names);
- one plain line under each screen title saying what the screen is for.

## 4.13 Laptop visitors

A reviewer may open the link on a laptop. On a wide screen, the app stays centred at phone size, with a small QR
code in the corner that opens it on a phone. A large explanatory panel was tried first and then cut to the small
corner code, because it was distracting.

---

Next: [Part 5 · Deployment, fallbacks and final polish](05-deploy-and-polish.md)
