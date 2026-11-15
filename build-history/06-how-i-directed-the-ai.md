# Part 6 · How I directed the AI

[← Part 5](05-deploy-and-polish.md) · [Back to Part 1](01-research-and-plan.md)

These are the things I told Claude Code while we built FINN, in the order they came up, written the way I
write: short and direct. Only obvious typos are fixed. Under each stage is what the AI did with them.

---

## Setting the bar

- keep analysing as you go, if something is weak tell me and make it better
- i dont want fast app, i want great app that can actually standout from apps made by the top brains of india
- do all the work yourself in the project, write it run it test it fix it
- this is our analysis and the prototype we made, take it and start from there
- ask me before installing anything or making accounts or pushing to github

**What the AI did:** went through our analysis and prototype, kept what was solid, wrote down the rules for the
project, checked every tool on my laptop and made a six-step plan.

## Checking in

- tell me the updates, how long to finish the app, when can i see first version
- we deploy at the end right? i want to see it working, improve it and then go to vercel
- can i see it on my phone? what is the deliverable and how do i submit
- first you finish all the deliverables you want to add in the app, then i will look into it
- i had to close the laptop for sometime, continue the work and tell me the updates

**What the AI did:** kept building task by task, told me where things stood in plain words, ran the app so I could
try it on my phone, and listed exactly what only I could do.

## Getting it online

- send me the steps of what to do for render, i will do my part
- its asking for card
- i did it with render, remove what you added yourself and dont do such things again
- this is the render link and the new key, check everything
- i mistakenly deployed without adding environment variables what to do
- give me the final links for app to open on laptop and phone

**What the AI did:** gave me step-by-step clicks, removed what I didn't want, tested the live server properly,
fixed the Vercel setting with one redeploy, and checked the real public link.

## The outside review

- do a critical analysis of these changes and see which ones are needed to make it a world class app, if needed work on them asap
- i feel the font size is too much its not looking premium, if you feel the same take action

**What the AI did:** sorted the review into what a reviewer notices first, what the brief asks for, and what was
safe to change before submitting, and worked through it in that order.

## The first screen

- you spoiled the first page, who wants to wake up to such a clumsy page?
- i want the first page as clean and as pretty as this
- if there is nothing in last three days also then keep it 24 hours, 7 days and then custom
- small line "today nothing new" and then a proper "earlier this week" section, no big empty card

**What the AI did:** rebuilt the top of the screen, brought back the look I liked while keeping the new stuff, hid
the empty time options and fixed the empty state.

## How it looks and feels

- the app is looking very tacky because of the colour, can we mellow down the neon green? apps usually have plain background so keep the tinge only near the logo
- make sure things are easy to navigate, its very hard to understand, add movements to be smooth like good apps have
- the floating bar at bottom looks very bulky make it slim and sleek. now its kinda getting lost in the page give it a little 3d view
- where you write the company name you can highlight it a bit by putting in a box
- remove the voice part that tells the news, sounds too mechanical and over engineered

**What the AI did:** softer green on a plain background, labels on every tab and smooth transitions, a slimmer
raised bottom bar, company names in boxes you can tap, and the voice taken out.

## The logo

- this is how i want my logo, make the FINN a little more thin the strokes are thick
- remove the updated time and the logo at top left is not changed
- when someone opens the app first screen should have tiny animation where logo is formed for 2-3 second
- its still flickering in the phone

**What the AI did:** redrew my logo cleanly, made the lettering lighter, made sure every phone loads the new icon,
added the opening animation, and found what was really causing the flicker on iPhone and fixed it.

## Small things on each screen

- reduce the font size, the box of any holding and 3x is almost clashing
- see here if anything could be done, make it a bit less messy
- things look clashing here also
- the size of the filing box is weirdly small. the ask is weirdly small
- the buttons dont look changeable, not asking me to click, make it better. mute and normal are same, change colour for mute. movement is very bouncy make it smooth. just a lil bounce
- what is the need of cost meter, is it even needed? it feels very abrupt, think of best place and change

**What the AI did:** fixed each one, re-checked every screen after every change, and sent me a screenshot each time.

## Bigger upgrades

- Do these seven in this order and put each one live as soon as it's ready: FINN's take on company pages,
  pre-load more big companies, show people their place in the queue, make the daily refresh safer, label the charts
  and let me tap for values, check direction-only promises, and add bank numbers.
- okay as you recommend
- apply these UI changes, going live after each

**What the AI did:** built and shipped each one separately, and explained why the direction-only promise check was
safer to leave until after submitting.

## Charts

- make the graphs prettier, dont copy, take inspo of how pretty graphs can be
- i like this mountain kinda graph, mountain graphs with peaks to have a tinge of white dot
- make the colour a tad bit brighter with very tiny whitish dot at top, should look like reaching heights, increase the tinge of green
- only cash quality one

**What the AI did:** redesigned the charts, tried the mountain style, and kept it only for cash quality like I
decided.

## Wrapping up

- write how we made it, the thought process and how we used the AI
- highlight in the beginning that i self designed the logo, dont write dates
- frame the email for me fast

**What the AI did:** wrote this build history from the real work and drafted my covering email.

---

Next: [Part 7 · Every change, in order](07-every-change.md)
