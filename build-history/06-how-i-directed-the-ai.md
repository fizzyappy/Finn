# Part 6 · How I directed the AI

[← Part 5](05-deploy-and-polish.md) · [Back to Part 1](01-research-and-plan.md)

These are the instructions I gave Claude Code at each stage of the build, in order. They are my real requests,
edited for clarity and grammar; the meaning of each one is unchanged. Under each stage is what the AI did with it.

---

## Setting the bar

- Keep analysing your own work as you go. If something is weak, say so and improve it.
- I don't want a fast app. I want a great app that stands out against the best submissions in the country.
- Work directly in my project folder like an agent: write the code, run it, test it and fix it yourself.
- Here is our earlier analysis and prototype. Use it as the starting point.
- Ask me before installing anything, creating accounts, committing or pushing.

**What the AI did:** reviewed the earlier analysis and prototype, kept what held up, set the project rules, checked
every tool on my PC and wrote the six-task plan.

## Progress and priorities

- Tell me where we are, how long it will take, and when I can see the first version.
- We deploy at the end. First I want to see the app working, improve it, and only then put it on Vercel.
- Can I see it on my phone? What exactly are the deliverables, and how do I submit?
- Finish every deliverable you think the app needs first. Then I'll review it.
- Keep working while I'm away, and tell me what changed when I'm back.

**What the AI did:** worked through the tasks end to end, reported progress in plain language, ran the app on my
laptop for phone testing, and listed exactly what only I could do.

## Deployment

- Send me the steps for Render. I'll do the parts that need my account.
- Render is asking for a card. Find a way that works without one, or tell me my options.
- I've chosen Render. Remove the alternative you prepared, and don't build options I haven't asked for.
- Here is the Render address and a new key. Test everything from the cloud.
- I deployed to Vercel without the environment variable. What do I do now?
- Give me the final links to open the app on my laptop and on my phone.

**What the AI did:** gave click-by-click steps, removed the unrequested alternative, tested the live server end to
end, fixed the Vercel setting with one redeploy, and checked the app on the public link.

## The outside review

- Here is a detailed critical review of the app. Analyse which points actually matter for the challenge and for a
  world-class app, then work on those first.
- The font size feels too large and doesn't look premium. Take action if you agree.

**What the AI did:** ranked the review's points by what a reviewer sees first, what the brief asks for, and what was
safe before submission, then fixed them in that order.

## The first screen

- The first page looks clumsy. Nobody wants to wake up to that.
- I want the first page as clean and polished as the original version.
- If the last three days are also empty, show only 24 hours, 7 days and Custom.
- Start with a slim "nothing new today" line and a clearly labelled "earlier this week" section, with no empty card
  and no contradictory zeros.

**What the AI did:** rebuilt the header, restored the look I preferred while keeping the new content, hid empty time
windows and replaced the empty state.

## Look and feel

- The neon green looks tacky. Tone it down. Most good apps use a plain background, so keep the tint only near the
  logo.
- Make the app easy to navigate and understand, with smooth, app-like movement.
- The bottom bar is bulky. Make it slimmer and cleaner. Now it gets lost on the page, so give it a slight 3D look.
- Highlight the company name on each card, for example in a box.
- Remove the voice that reads the news. It sounds mechanical and over-engineered.

**What the AI did:** a calmer accent and plain background, labelled tabs and smooth transitions, a slimmer raised
bottom bar, company names in tappable chips, and the voice feature removed.

## Identity

- This is how I want my logo to look. Make the FINN lettering thinner.
- Remove the updated time from the header. The logo in the top-left corner hasn't changed on my phone.
- When the app opens, the logo should form in a short animation of two to three seconds.
- It's flickering on my phone. Fix it properly.

**What the AI did:** redrew my logo as a vector, lightened the wordmark, forced every device to load the new icon,
built the opening animation, and found and fixed the real causes of the flicker on iPhone.

## Details on each screen

- The value boxes in the alert sentence are almost touching. Reduce the font size.
- Make the alert history rows less messy.
- The research list looks cluttered.
- The Filing button is oddly small. The Ask button is oddly small too.
- The Mute / Normal / Boost buttons don't look clickable. Mute and Normal look the same, so give them different
  colours. The slide is too bouncy; keep just a little bounce.
- Does the cost meter need to be in the app? If it does, put it in the best place.

**What the AI did:** fixed each one, re-checked every screen after each change, and sent me a screenshot.

## Product upgrades

- Do these seven, in this order, and put each one live as soon as it's done: FINN's take on company pages,
  pre-research more large companies, a queue position, a safer daily refresh, labelled charts with tap-to-read
  values, directional promise checks, and bank numbers for lenders.
- Directional promises: go with your recommendation and leave them for after the submission.
- Apply these fifteen interface changes, putting each live as soon as it's done.

**What the AI did:** built and shipped each item separately, and explained why the directional promise check was
safer to postpone.

## Charts

- Make the graphs prettier. Don't copy anyone. Show how good charts can look.
- Use a mountain chart, with a small white dot on each peak.
- The alert peaks should look like they are reaching heights, with a bit more green.
- Only the cash-quality chart should be a mountain. Everything else stays as it was.

**What the AI did:** redesigned the charts, tried mountain styles, and kept the mountain only for cash quality, as I
decided.

## Submission

- Write the build history explaining how we worked, why each decision was made and how we used AI.
- Credit my logo first. No dates, no emojis, no outside references.
- Draft my covering email.

**What the AI did:** wrote this build history from the real work and drafted the covering email.
