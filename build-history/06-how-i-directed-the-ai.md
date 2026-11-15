# Part 6 · How I directed the AI

[← Part 5](05-deploy-and-polish.md) · [Back to Part 1](01-research-and-plan.md)

These are the things I actually told Claude Code while we built FINN, in the order they came up. I've cleaned up
my spelling and grammar so they're easy to read, but they're still my words and my meaning. Under each stage is
what the AI did with them.

---

## Setting the bar

- Keep analysing as you go. If something looks weak, tell me and make it better.
- I don't want a fast app. I want a great one, something that actually stands out next to apps made by the best
  people in the country.
- Do the work yourself, in the project folder. Write it, run it, test it, fix it.
- Here's our analysis and the prototype we made. Start from there.
- Ask me before you install anything, make accounts, or push to GitHub.

**What the AI did:** went through our analysis and prototype, kept what was solid, wrote down the rules for the
project, checked every tool on my laptop and made a six-step plan.

## Checking in

- Where are we? How long until it's done, and when can I see the first version?
- We'll deploy at the end. First I want to see it working and improve it, then we go to Vercel.
- Can I open it on my phone? What exactly do we have to submit, and how?
- Finish everything you think the app needs first. Then I'll sit down and look at it.
- I had to close my laptop for a bit. Keep going, and tell me what changed.

**What the AI did:** kept building task by task, told me where things stood in plain words, ran the app so I could
try it on my phone, and listed exactly what only I could do.

## Getting it online

- Send me the Render steps. I'll do the bits that need my account.
- Render is asking for a card. What are my options?
- I'm going with Render. Take out the other thing you set up, and don't build stuff I didn't ask for.
- Here's the Render link and a fresh key. Test everything from the cloud.
- I deployed on Vercel but forgot the environment variable. What now?
- Just give me the final links, one for my laptop and one for my phone.

**What the AI did:** gave me step-by-step clicks, removed what I didn't want, tested the live server properly,
fixed the Vercel setting with one redeploy, and checked the real public link.

## The outside review

- Here's a detailed review of the app. Figure out which points actually matter for the challenge and for making
  this world class, and do those first.
- The font feels too big, it doesn't look premium. Fix it if you agree.

**What the AI did:** sorted the review into what a reviewer notices first, what the brief asks for, and what was
safe to change before submitting, and worked through it in that order.

## The first screen

- The first page looks clumsy. Who wants to wake up to that?
- I want it as clean and pretty as the earlier version.
- If there's nothing in the last three days either, just show 24 hours, 7 days and Custom.
- Put a small "nothing new today" line, then a proper "earlier this week" section. No big empty card, no zeros
  that don't make sense.

**What the AI did:** rebuilt the top of the screen, brought back the look I liked while keeping the new stuff, hid
the empty time options and fixed the empty state.

## How it looks and feels

- The neon green looks tacky, tone it down. Apps usually have a plain background, so keep the green just near the
  logo.
- It's hard to find your way around. Make it easy, and make it move smoothly like a good app.
- The bottom bar is too bulky, make it slimmer. Now it's getting lost on the page, give it a bit of a 3D feel.
- Make the company name stand out on each card, maybe put it in a box.
- Take out the voice that reads the news. It sounds mechanical and over the top.

**What the AI did:** softer green on a plain background, labels on every tab and smooth transitions, a slimmer
raised bottom bar, company names in boxes you can tap, and the voice taken out.

## The logo

- This is how I want my logo. Make the FINN letters a little thinner.
- Remove the updated time at the top. And the logo top-left still hasn't changed on my phone.
- When someone opens the app, I want the logo to form in a tiny animation, two or three seconds.
- It's still flickering on my phone. Sort it out properly.

**What the AI did:** redrew my logo cleanly, made the lettering lighter, made sure every phone loads the new icon,
added the opening animation, and found what was really causing the flicker on iPhone and fixed it.

## Small things on each screen

- The boxes in the alert sentence are almost touching, make the text smaller.
- The alert history looks messy, clean it up.
- The research list looks cluttered.
- The Filing button is weirdly small. So is the Ask button.
- The Mute / Normal / Boost buttons don't look like you can tap them. Mute and Normal look the same, give them
  different colours. The slide is too bouncy, keep just a little bounce.
- Do we even need the cost meter? If yes, put it somewhere that makes sense.

**What the AI did:** fixed each one, re-checked every screen after every change, and sent me a screenshot each time.

## Bigger upgrades

- Do these seven in this order and put each one live as soon as it's ready: FINN's take on company pages,
  pre-load more big companies, show people their place in the queue, make the daily refresh safer, label the charts
  and let me tap for values, check direction-only promises, and add bank numbers.
- For the direction-only promises, go with what you think is right.
- Now do these fifteen interface changes, each one live as soon as it's done.

**What the AI did:** built and shipped each one separately, and explained why the direction-only promise check was
safer to leave until after submitting.

## Charts

- Make the graphs prettier. Don't copy anyone, just show me how good charts can look.
- I like mountain charts, with a tiny white dot on each peak.
- The alert peaks should feel like they're reaching up, with a bit more green.
- Only the cash-quality chart should be a mountain. Leave everything else as it was.

**What the AI did:** redesigned the charts, tried the mountain style, and kept it only for cash quality like I
decided.

## Wrapping up

- Write up how we built this: how we worked, why we made each decision, and how we used AI.
- Put my logo first. No dates, no emojis, nothing about anyone else's work.
- Write my email for me too.

**What the AI did:** wrote this build history from the real work and drafted my covering email.

---

Next: [Part 7 · Every change, in order](07-every-change.md)
