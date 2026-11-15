# Part 4: Designing the app and the user experience

This part is about how FINN looks, moves and feels, and every round of
back-and-forth it took to get there. Almost all of it happened the same way: I
opened the app on my phone, something felt off, I took a screenshot and said
what bothered me in plain words. Claude turned that into a specific change, and
I looked again.

Lines starting with ">" are my everyday instructions. Where my original wording
was already clear I've kept it close to how I said it; otherwise it's tidied up.
Lines starting with "●" are what Claude did, what it suggested, and what I
decided.

---

## 4.1 The logo

I designed the FINN logo myself. I drew it by hand first, then refined it in
Adobe Illustrator with AI tools until the proportions felt right.

The mark is a slanted F made of two arms, and each part of it means something.

The upper arm is the longer one, and it reaches further out. It stands for
everything that flows into FINN: corporate announcements, annual reports,
earnings calls, market moves and management guidance. It's the breadth of
information an investor deals with every day.

The middle arm is deliberately shorter. FINN doesn't hand back everything it
receives. It narrows the flood down to what deserves attention, and the shorter
arm is that narrowing.

There's a second way to read the two arms, and it's the one I like most. The
upper arm is what management said. The middle arm is what the numbers actually
show. ENAM's brief cares most about comparing promises with delivery, and that
gap is exactly what FINN's research page measures.

The dark gap between the arms matters too. Without it the F would look like two
ribbons stuck together. It stands for the problem FINN solves: the space between
information that exists and information that deserves an investor's attention.

The slant is mostly a style choice, and I'm not going to pretend every angle
encodes a formula. It does give a horizontal letter a sense of moving forward,
which fits an app that watches for what changes instead of storing history. The
curved transitions make the letter read as one continuous form, the way raw
information gets turned into something useful.

The colours carry the same idea. Mint green is clarity and the signals that
matter. A darker green gives depth, the analytical layers underneath. The
lighter top surface is information coming in. A soft inner shadow separates the
layers. The deep forest-green background gives it a serious, institutional feel.
The whole app's colour scheme comes from these colours.

### Getting the logo into the app

The app's first logo was a placeholder Claude had made: a fin cutting through a
waterline. Once my own design was ready, I sent it over.

> this is how i want my logo to look like. just make the FINN a little more
> thin, the strokes are a bit thick right now

● Claude redrew my design as a crisp vector, so it stays sharp at every size,
  with the FINN letters thinner and spaced a little wider. It sent a preview
  first and waited for my okay before touching the app.

● Once I approved it, the new logo went everywhere: the header, the home-screen
  icon, the browser tab, the quiet-day card and the loading screen.

> remove the updated time, and the logo at top left is not changed

● Two things were going on. The "Updated" time came off the header. The logo had
  actually changed on the server, but my phone was showing a saved copy of the
  app (FINN caches itself so it opens fast). Claude renamed the logo files so
  every phone would be forced to load the new one, and told me to remove and
  re-add the home-screen icon, since phones hold on to old icons.

---

## 4.2 The first version

The first version was built from my two UI reference images and the design
direction from the research phase: a dark, green-tinted glass interface with
frosted cards, a mint glow, pill-shaped chips and a floating bottom bar. I
wanted it calm and premium, dense with information without feeling crowded.

● Claude built it as a React and Vite progressive web app, so it installs on a
  phone like a native app. It used hand-written CSS and Framer Motion for
  animation, so I had full control over the look and the bundle stayed small
  (about 100 KB compressed). The UI work used the Impeccable and frontend-design
  skills I'd installed.

● The first version had four screens (Brief, Research, Alerts, Settings),
  swipe-to-clear cards, cards that flip to show why they ranked, a live alert
  slider with a 90-day preview, and research pages that fill in section by
  section. Claude checked 18 screenshots at iPhone size with no errors and
  opened it in my laptop's browser, with instructions to switch the browser into
  phone view.

> first you finish all the deliverables you want to add in the app and then i'll
> go and check it. i want you to finish it first, then i'll look into it

● So Claude finished everything first: a strict review of every screen, two
  extras ("Ask about this company" and "Play my brief", which read the brief
  aloud), and the README, demo script and email draft. Then I reviewed it all in
  one go.

---

## 4.3 The critique, and what we chose to act on

Once the app was live, I put it through a detailed critique, screen by screen,
and asked Claude to judge which points actually mattered.

> I want you to do a critical analysis of these changes and see which ones are
> on par with what the problem statement needs to make it a world-class app. If
> you think the changes are needed, work on them asap. I also feel the font size
> is too big, it's not looking premium. If you feel the same, do something about
> it.

The critique's verdict was clear. The engine was roughly 90% of the way there
and the product surface about 70%. It scored the architecture 9/10, judgment and
honesty 9.5/10, cost efficiency 9/10, but the Brief only 6.5/10 and visual
design 7.5/10. Its biggest points:
- the first screen a reviewer saw could be empty ("0 filings · 0 matter") with a
  full green ring that read as "done!";
- the 3-day view contradicted itself, saying "Quiet" right above "Worth knowing
  · 1";
- the results card and the management card were hidden behind a custom 14-day
  window;
- bull and bear read like a template, and HDFC Bank's growth included its
  merger;
- mint green was used for everything, so nothing stood out;
- a long list of small wording and format issues.

● Claude went through it and split it into "doing now" and "skipping today",
  with reasons.

Doing now, in order:
1. The first screen is never empty. If a window has nothing important, it shows
   what mattered in the last 7 days instead, and the counts always add up.
2. A pinned "Latest results" strip at the top of the Brief.
3. Hand-checking the two numbers a reviewer could catch: Reliance's +11.6% day
   and CDSL's "4 dodged".
4. A sharper bull and bear: Python works out the slowdown, the margin squeeze
   and the merger effect, and the model only phrases them.
5. A calmer look: smaller, tighter fonts; numbers in a cleaner font that lines
   up; much less mint and glow.
6. A wording clean-up: dates like "12 Nov 2026", quarters like "Q2 FY27", ₹
   everywhere, "Updated" instead of "snapshot", and no code words like bse_api
   in the UI. The server address box moved into a hidden "Developer" section.
7. The alert slider shows the plain ±% for each stock.
8. Only my Vercel site can call the backend, with a limit per visitor.
9. The email gets "What I left out" and "What's next".

Skipped for that day, because they were too big or risky so close to submission:
the directional promise ledger, full bank metrics, a job queue and a sticky jump
bar.

● All of it went live with 115 tests passing and 20 screens re-checked. The hand
  checks came back clean: every CDSL "dodged" flag was an explicit refusal, and
  Reliance's +11.6% was a real move, not a data error. The HDFC management card
  stayed without a bio, because that filing was an RBI letter with no profile in
  it, and FINN doesn't invent one.

---

## 4.4 The first page, three times

This was the biggest design argument of the build, and I'm glad I pushed.

> you spoiled the first page. who wants to wake up to such a clumsy page?

● Claude agreed the top was cramped. Too many things were competing at once: the
  ring, a two-line headline, a subline, counts, Play, a tip banner, the chips
  and a "score 0.83" tag. It proposed a calmer layout and shipped it: just "Your
  brief" with one line under it ("3 matter · 1 to clear · 20 filings"), a small
  ring, no tip box, and a single plain line when a window was quiet.

● It also owned up to a slip: it had said it would show me a screenshot first,
  but the change went live straight away.

It was calmer, but it had lost what I liked about the app. I sent a screenshot
of the original look.

> i want the first page as clean and as pretty as this

● Claude read that as: bring back the original style (the big glowing ring, the
  bold two-line headline, the mint selected chip, the soft glow, one large airy
  card with the FINN mark, the mint pill in the bottom bar) but keep the
  improved content underneath it. Results always show, the brief is never empty,
  and the wording stays clean. It also kept out the two things that had looked
  unfinished in the old version: a paragraph about the exchanges refusing
  connections, and a cut-off "Custom" chip.

● The quiet card now ends with "Here is what mattered in the last 7 days", and
  real cards follow, so the page is calm but never empty.

---

## 4.5 Navigation and motion

> make sure the things in the app are easy to navigate. it's very hard to
> navigate and understand. add more interactive things, movements should be
> smooth like good apps have

● Easier to navigate:
- every bottom tab shows its name: Brief, Research, Alerts, Settings;
- each screen has one plain line under its title saying what it's for;
- company pages have "← All companies" at the top;
- on a company page, a bar sticks to the top as you scroll and jumps to Ask,
  Promises, Answers, Numbers, Bull/bear or Sources.

● Smoother:
- screens slide left or right depending on which way you're going;
- sections fade in gently as you scroll;
- buttons and rows react softly when tapped, the way native apps do.

---

## 4.6 Clashes on small screens

> maybe you can reduce the font size. the box of any holding and the 3x are
> almost clashing

> see here if anything could be done, make it just a bit less messy

● On Alerts, the alert sentence got smaller so its pills stopped touching. The
  alert list became two tidy lines per row: the company in bold with the date
  under it on the left; the % move in green or red on the right with "3.0× usual
  move · 3.5× volume" in small grey underneath. The % shows one decimal so the
  numbers line up in a column.

> things look clashing here also

● The Research list became a clean two-column row per company. On the left: the
  ticker in bold, the company name in grey, then one short line like "Portfolio
  · next due FY27 · call Nov 2026" (research-only companies say "Not held"). On
  the right: the pills ("1/1 kept", "4 dodged", "11 tracked") stacked neatly.
  The empty "no targets" pill was removed.

● To stop clashes coming back, the Playwright screen check fails the build on
  text overflow. A clash became a failing test rather than something I had to
  keep spotting.

---

## 4.7 The opening animation

> i want that when someone opens up the app, the first screen has a tiny little
> animation where the logo is formed, for like 2 to 3 seconds

● The first version took about 2.5 seconds: the top arm of my F slides in, the
  lower arm follows and the F locks together, "FINN" fades in with its letters
  drawing together, a small tagline ("what matters in your holdings") appears,
  and it all fades into the Brief. It plays once per visit and a tap skips it.

> its not coming properly on my phone

● Claude asked what exactly I saw (no animation, jumpy, wrong place?) and
  suggested a screen recording.

> it comes, flickers and goes in like a couple of seconds

● Round two found two causes. A small still logo flashed for a split second
  before the animation started on top of it, so now the screen starts plain dark
  and the logo forms from nothing. And Safari on iPhone is bad at moving parts
  inside a single drawing, so each arm now moves on its own in a way Safari
  handles smoothly. Claude also pointed out that if Reduce Motion is on, the app
  deliberately plays a simpler fade.

● A small follow-up made the ending calmer: about 3 seconds, ending in a slow,
  soft fade instead of a quick zoom.

> its still flickering on the phone

● Round three went into the code properly and found the real cause. The app was
  loading every Brief card behind the animation while it played, which is heavy
  work on a phone, so the animation stuttered and got cut short. The "FINN"
  letters also switched font halfway through, which looked like a flicker. The
  fix: build the animation into the page itself so it plays from the first
  frame, load the app only after the animation finishes, and use a font that's
  already loaded. It now plays cleanly for about 3.5 seconds.

A desktop browser hid this bug completely. After this, I checked every animation
on my phone.

---

## 4.8 The cost meter

> what is the need of cost meter, is it even needed?

● Claude's view: a normal user doesn't need it, but this submission does. ENAM
  is judging how sensibly AI is used, and the meter shows with real numbers that
  FINN made a few hundred AI calls for $0, because Python does the maths and the
  model is only called when needed. It suggested keeping it as a small, quiet
  section at the bottom of Settings, and asked me to choose between that and
  removing it.

> it feels very abrupt when it comes, don't you think so? if you think we should
> show it in the app, then think about what the best place is and change it
> accordingly

● Settings now opens with what matters to the user: their portfolio, then which
  announcement types reach them, then where the data comes from. The cost became
  one calm line near the bottom, under "What it costs to run": "$0 spent · 376
  AI calls · 67% from cache · 1.1M tokens". The big glowing box is gone.

● While doing this, Claude caught two problems and told me. The morning's
  automatic refresh had shrunk the cost numbers to just its own run; they now
  always show the whole build. And its last few "20 screens, 0 errors" reports
  hadn't been complete, because the test script had been stopping halfway since
  the jump bar was added. It fixed the script and re-ran every screen properly:
  20 screens, no errors.

---

## 4.9 The bottom bar

> the floating bar at the bottom for brief, research and alerts looks very
> bulky. can we make it a little more slim and sleek so it looks cleaner and
> more appealing?

● About 25% shorter, with smaller icons and labels and less padding. The
  selected pill glows more softly, the border and shadow are lighter, and the
  labels stay so it's still easy to read.

> its kinda getting lost in the page. can we give it a little 3d view?

● The bar is now slightly lighter at the top and darker at the bottom, with a
  thin lit edge and a deeper shadow, so it floats above the page. The selected
  pill has the same raised look.

---

## 4.10 Removing the voice brief

> remove the voice part please, that reads out the news. it sounds too
> mechanical and over-engineered

● Gone completely. The Brief header now shows just the ring, the title and the
  counts, and the README and demo script no longer mention it. In a finance app,
  a robotic voice costs trust.

---

## 4.11 Company names in boxes

> where you write the name of the company in its news, highlight it a bit by
> putting it in a box or something

● Company names now sit in a small tag with a soft tint, on the big cards, the
  "Worth knowing" rows, Unusual moves and Recent alerts.

---

## 4.12 Colour

> i feel the app in general is looking very tacky because of the colour. can we
> slightly mellow down the neon green? is it too bright? will it look better
> then? what's your opinion? also, in the background some places have a hint of
> green. i think apps usually have a very plain background, so should i make
> mine plain black, and keep that tinge only near the logo? will that improve
> the user experience?

● Claude agreed with both and explained why. The green was close to neon and on
  too many things at once, so nothing stood out. It suggested a calmer, slightly
  muted mint, used only where it means something: the selected tab, the main
  button and price rises. Everything else white or grey, so green stands out
  because it's rare.

● On plain black it agreed with one tweak: near-black rather than pure black.
  Pure black makes white text look harsh and smears on many phones when you
  scroll, which is why most premium dark apps use near-black. The green tinge
  would stay only as one soft glow behind the logo and ring at the top, and the
  cards would become a neutral dark grey instead of green-tinted glass.

> yes yes do it

● The calmer colours went live: a softer sage-mint, lighter glows, a gentler red
  for falling prices, a plain near-black background, and a faint tint only by
  the logo. Text still passed the readability check. The colours now follow the
  logo's palette.

---

## 4.13 Time filters that adapt

> if there is nothing in the last three days either, then keep it as last 24
> hours, 7 days and then custom

● The time chips now only show windows that have news. "24h", "7 days" and
  "Custom" are always there; "Since last look" and "3 days" appear only when
  something in them needs attention.

---

## 4.14 The Mute / Normal / Boost switch

> the announcements that are set to Normal in settings, the buttons don't look
> like they can be changed to Mute or Boost. the clicking interface isn't
> appealing, it's not asking me to click. can you make it better?

● It became a proper sliding switch, like the toggles in iPhone Settings. A
  raised button sits on the current choice and slides when you tap another. The
  header now says "tap to change".

> mute and normal look the same. you can change the colour for mute or something

● Each choice got its own colour: Mute a soft red, Normal grey, Boost green.

> in the announcements, the movement from mute to normal is very bouncy, make it
> smoother

● The highlight now glides across smoothly instead of bouncing.

> just a lil bounce

● A slight settle added back. Smooth, with a little life to it.

---

## 4.15 The numbered UI pass

Next, Claude went through a longer list of 28 possible UI changes and
recommended 12 for that night, small ones that each made the app clearer for a
reviewer, plus a fix for the custom date picker I'd noticed spilling off its
card. It listed what to skip and why: colours and time chips were already done;
I'd asked for the "Updated" time to go; compact results cards would hide one of
the two cards ENAM said they love; and new price and range charts would each
take hours on deadline night.

I sent the list as one numbered block:

> Apply these UI changes, going live after each:
> 0. Custom date picker: From/To boxes must fit inside the card without
> overlapping; the quick-pick chips must not be cut off; dates as "1 Nov 2026",
> not "2026-11-01".
> 1. Brief top: a slim "Today: nothing new" line, then a clearly labelled
> "Earlier this week" section with the 7-day cards (no big empty card, no
> contradicting zeros).
> 2. Replace the "score 0.83" chip on cards with "your X% holding"; keep the
> score inside Why?.
> 3. Add a small visible "Done" button next to Why? on each card (swipe still
> works).
> 4. Tapping a company name anywhere opens its Research page.
> 5. Alerts tab: "Recent alerts" first, the rule setup below.
> 6. Report card wording: "answered 51 of 51 questions" instead of "0/51
> dodged"; grey out zero tiles.
> 7. Research landing: "Your holdings" first, then "Other companies"; shrink the
> explainer to one line.
> 8. Results cards whose numbers are not verified: headline "Results filed ·
> numbers not verified", with the filing subject in small text.
> 9. Company page: move the Ask box to the end.
> 10. Brief header: a thin filter-funnel bar, e.g. "70 filings → 9 worth knowing
> → 2 need you".
> 11. One short sentence written by Python above each chart, e.g. "Revenue +9%
> YoY in Q2 FY27; profit +6%".
> 12. On wide (laptop) screens, a side panel with a QR code to the app and "FINN
> is built for your phone".
> 13. A one-line portfolio pulse under the Brief header, e.g. "11 up, 7 down vs
> Nifty this week".
> 14. Prettier charts.

● Items 0 to 11 went live first, then 13 and 14. The Brief now opens with a slim
  "Today: nothing new" line, then "Earlier this week", the funnel ("20 filings →
  3 worth knowing → 1 need you") and the pulse ("5 ahead, 13 behind the Nifty
  this week · biggest CDSL +8%"). Cards show "your 6% holding" and have a green
  Done ✓ button. Alerts opens with recent alerts. Research is split into "Your
  holdings" and "Other companies". 119 tests passed and all 20 screens were
  clean.

> the size of the filling box is weirdly small

> the ask is weirdly small

● The "Filing ↗" button became the same size as "Why?" and "Done ✓" next to it.
  The Ask button became full size, the same height as its text box, and the
  suggested questions wrap instead of being cut off.

● For item 12, Claude asked before installing one small Python tool (segno) to
  make the QR image. My laptop's safety check blocked the install the first
  time, so the panel shipped with the app link in large text instead, and the QR
  came in a later pass.

---

## 4.16 Charts

> make the graphs prettier

> don't copy anyone, take inspiration from how pretty graphs can be

● The new charts were in FINN's own style. Revenue bars have a gradient and grow
  in one by one, with a gold margin line drawing itself and tap-to-see values.
  Cash vs profit got matching bars and a proper legend. Promises got a target
  band with a marker that slides in, green when met and red when missed (L&T
  shows 11.8% against a 15% target). The alerts strip got rounded gradient bars.
  Older periods are greyed out, the latest highlighted, and every chart has a
  one-line takeaway above it written by Python.

### The alert peaks

> make the colour of this just a tad bit brighter, and add a very very tiny
> whitish dot at the top

> it should look like it's reaching heights

> increase the tinge of green in this

● The alert bars became rising peaks: deep green at the base and bright mint at
  the top, a soft glow, a tiny white dot on each tip, and they rise when the
  screen opens.

### The cash-quality mountain

> i don't like the cash quality graph

● Claude asked what bothered me and offered two replacements: a single line of
  "cash earned for every ₹1 of profit" with a one-sentence verdict, or just a
  sentence and a badge with no chart.

> i like this mountain kind of graph

● Claude suggested using the mountain style in three places: cash quality, the
  margin line, and a new 90-day price chart against the Nifty at the top of each
  company page.

> i am not able to visualise them, so do what you find best, and if you want my
> opinion, show me what you mean

● It drew a picture with made-up numbers to show the look.

> none of them look like mountain graphs

● Fair. The lines were too smooth. A mountain chart needs jagged peaks drawn
  from real data points with a solid fill underneath, so Claude redrew it with
  straight, jagged segments and a strong gradient.

> i want mountain graphs, with the peaks having a tinge of a white dot

● It added a tiny glowing white dot on every peak and a bigger one on the latest
  point, and I sent the full spec for all three mountains to build.

While it was being built, I changed my mind about how far to take it. Claude had
also made the cash-quality chart simpler in the meantime (bars against a 1×
line), which wasn't what I wanted.

> i did not want it simpler. i wanted it to be a mountain chart. no other graph
> needs to be a mountain chart

> only the cash quality one

● The messages crossed: the 90-day price mountain went live just before my "only
  cash quality" message arrived, and then the build got it backwards, turning
  revenue and profit into mountains while leaving cash quality as bars. Claude
  said so plainly and gave me one exact line to send.

> Undo: put revenue and net profit back as bars, and remove the 90-day price
> chart. Make ONLY the cash-quality chart a mountain (green fill, jagged peaks,
> tiny white dots on peaks, dashed ₹1 line). Nothing else.

● That fixed it. Revenue and profit are bars again, the price chart is gone, and
  only cash quality is a mountain: green fill, jagged peaks, white dots, and a
  dashed line at ₹1. Below that line, profit isn't turning into cash.

When I changed my mind halfway, explaining again at length didn't help. A short
instruction that said exactly what to leave alone fixed it in one step.

### The backtest card

> put this before recent alerts, on the alerts page

● The "If this had been on" backtest card (21 alerts in 90 days, about one a
  week) now comes before the list of recent alerts, so you see how often the
  rule fires before what it caught.

---

## 4.17 The laptop view

Most reviewers will open the link on a laptop first, even though FINN is a phone
app. The first wide-screen version was a side panel saying "FINN is built for
your phone", with the link in large text and one line about each tab. Later the
QR code went in.

> make this very short, just a small logo in one corner to tell them

● It's now just a small QR code in the bottom-left corner: "Best on your phone:
  scan to open".

---

## 4.18 Ideas I cut on purpose

Four more ideas came up near the end, and Claude checked each one:
- filter chips on the Research list (All · My holdings · Kept promises · Dodged
  questions · Banks);
- smaller, tabular numbers in the results table;
- green and red tags on news, with one safety tweak: never "buy" or "sell", only
  "Positive for shareholders" or "Negative for shareholders", set by clear
  rules, because buy/sell language reads as investment advice under SEBI rules;
- collapsible long cards, with "Needs your attention" staying open.

All four were good. With about 10% of my credits left, I cut them and listed
them as future work, along with a full stress test of the Gemini quota. I kept
one quick live check that Ask still worked.

---

## 4.19 How I worked on design with AI

Every change here started on my phone. I sent screenshots, not descriptions.
When I knew exactly what I wanted, I sent a numbered list. When I didn't, I
asked for Claude's opinion or asked it to show me pictures, then decided. And
when the AI got something wrong, I said so straight away and gave a short,
scoped fix.

The app looks the way it does because I kept saying "no, not quite" until it
matched what I had in my head.

Next: Part 5, deployment, fallbacks and the finish.

