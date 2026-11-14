// Screenshot every screen and state at iPhone size, collect console errors, run axe.
// Usage: npm run build && node scripts/screenshots.mjs   (serves dist/ with vite preview)
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright-core";
import AxeBuilder from "@axe-core/playwright";

const OUT = new URL("../screenshots/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
mkdirSync(OUT, { recursive: true });
const BASE = "http://localhost:4173";
const scale = Number(process.env.SCALE || 2);

const server = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--port", "4173", "--strictPort"],
  { cwd: new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"), stdio: "ignore" });
const stop = () => { try { server.kill(); } catch { /* already gone */ } };
process.on("exit", stop);
process.on("uncaughtException", (e) => { console.error(e); stop(); process.exit(1); });
process.on("unhandledRejection", (e) => { console.error(e); stop(); process.exit(1); });
for (let i = 0; i < 60; i++) {
  try { if ((await fetch(BASE)).ok) break; } catch { /* not up yet */ }
  await new Promise((r) => setTimeout(r, 500));
}

const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: scale, isMobile: true, hasTouch: true,
  reducedMotion: "no-preference", colorScheme: "dark" });
const errors = [];
const axe = {};
const shots = [];

async function fresh(hash = "") {
  const page = await ctx.newPage();
  page.setDefaultTimeout(120000);   // 2x full-page captures of glass-heavy pages are slow
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${hash}: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${hash}: ${e.message}`));
  await page.goto(`${BASE}/#${hash}`);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(900);
  return page;
}
async function shot(page, name, full = true) {
  await page.waitForTimeout(450);
  const path = `${OUT}${name}.png`;
  await page.screenshot({ path, fullPage: full });
  shots.push(name);
}
async function audit(page, name) {
  const r = await new AxeBuilder({ page }).disableRules(["color-contrast"]).analyze();
  const contrast = await new AxeBuilder({ page }).withRules(["color-contrast"]).analyze();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  axe[name] = {
    violations: r.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help })),
    contrast: contrast.violations.reduce((a, v) => a + v.nodes.length, 0),
    contrast_examples: contrast.violations.flatMap((v) => v.nodes.slice(0, 3).map((n) => n.target.join(" "))).slice(0, 4),
    horizontal_overflow_px: overflow,
  };
}

// 1. Brief: default, 14-day window, flipped "why", checks open, swipe-cleared, all-clear
let p = await fresh("brief");
await shot(p, "01-brief-since-last-look", false); await audit(p, "brief");
await p.getByRole("button", { name: "Custom" }).click();
await p.getByRole("button", { name: "Last 14 days" }).click();
await shot(p, "02b-brief-date-range-picker", false);
await p.getByRole("button", { name: "Show this range" }).click();
await shot(p, "02-brief-14d-results-cards");
const verified = p.locator("button.verified").first();
if (await verified.count()) { await verified.click(); await shot(p, "03-brief-results-checks-open", false); }
await p.getByRole("button", { name: /Why am I seeing/ }).first().click();
await shot(p, "04-brief-why-flipped", false);
await p.getByRole("button", { name: "Back" }).first().click();
// real swipe gesture on the first card
const card = p.locator(".swipe-wrap").first();
const box = await card.boundingBox();
if (box) {
  await p.mouse.move(box.x + 60, box.y + 60); await p.mouse.down();
  for (let i = 1; i <= 10; i++) { await p.mouse.move(box.x + 60 + i * 25, box.y + 62); await p.waitForTimeout(16); }
  await p.mouse.up();
}
await shot(p, "05-brief-after-swipe-clear", false);
for (let i = 0; i < 12; i++) {
  // the screen-reader buttons are visually hidden, so trigger them as assistive tech would
  const n = await p.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find((x) => x.textContent === "Clear this card");
    if (b) b.click();
    return b ? 1 : 0;
  });
  if (!n) break;
  await p.waitForTimeout(300);
}
await shot(p, "06-brief-youre-clear", false);
await p.getByRole("button", { name: "Bring cards back" }).click().catch(() => {});
await p.close();

// 2. Quiet day (simulated data: a brief with nothing material)
p = await ctx.newPage();
await p.route("**/data/brief_since_last_look.json", async (route) => {
  const real = await (await fetch(`${BASE}/data/brief_since_last_look.json`)).json();
  await route.fulfill({ json: { ...real, quiet: true, hero: [], one_liners: [], alerts: [], header: { ...real.header, matter: 0, hero: 0, alerts: 0 } } });
});
p.on("pageerror", (e) => errors.push(`quiet: ${e.message}`));
await p.goto(`${BASE}/#brief`); await p.waitForLoadState("networkidle"); await p.waitForTimeout(800);
await shot(p, "07-brief-quiet-day", false);
await p.close();

// 3. Research: intro, a company (report card + ledger), expanded ledger row, HAL, offline company
p = await fresh("research");
await shot(p, "08-research-intro", false); await audit(p, "research-intro");
await p.getByLabel("Search any NSE company").fill("asian pa");
await shot(p, "09-research-autocomplete", false);
await p.goto(`${BASE}/#research/LT`); await p.waitForTimeout(1200);
await shot(p, "10-research-LT-full"); await audit(p, "research-LT");
const row = p.locator("button.ledger-row").first();
await row.click(); await p.waitForTimeout(400);
await row.scrollIntoViewIfNeeded();
await shot(p, "11-research-LT-ledger-row-open", false);
// Ask about this company (live backend on this PC; cached answer)
const askBox = p.getByLabel(/Ask a question about/);
if (await askBox.count()) {
  await askBox.fill("Did they meet their FY26 revenue growth guidance?");
  await p.getByRole("button", { name: "Ask", exact: true }).click();
  await p.locator(".quote, .notice").filter({ hasText: /guidance|sources|won't|engine/i }).last().waitFor({ timeout: 90000 }).catch(() => {});
  await askBox.scrollIntoViewIfNeeded();
  await shot(p, "11b-research-ask", false);
}
await p.goto(`${BASE}/#research/HAL`); await p.waitForTimeout(1200);
await shot(p, "12-research-HAL-full");
await p.evaluate(() => localStorage.setItem("finn.api", JSON.stringify("off")));   // show the true offline state
await p.goto(`${BASE}/#research/ZOMATOX`); await p.waitForTimeout(1500);
await shot(p, "13-research-not-in-snapshot", false);
await p.evaluate(() => localStorage.removeItem("finn.api"));
await p.close();

// 4. Research cold start against a simulated live backend (stages + tables first)
p = await ctx.newPage();
p.on("pageerror", (e) => errors.push(`cold: ${e.message}`));
let polls = 0;
const lt = await (await fetch(`${BASE}/data/research/LT.json`)).json();
await p.route("https://finn-api.test/**", async (route) => {
  const u = new URL(route.request().url());
  if (u.pathname === "/health") return route.fulfill({ json: { ok: true } });
  if (u.pathname.startsWith("/research/") && route.request().method() === "POST")
    return route.fulfill({ json: { id: "job1", ticker: "DEMO", status: "running", stage: "resolving", progress_pct: 13 } });
  if (u.pathname === "/research/jobs/job1") {
    polls += 1;
    const stage = polls < 2 ? "fetching tables" : "reading transcripts";
    return route.fulfill({ json: { id: "job1", ticker: "DEMO", status: "running", stage, progress_pct: polls < 2 ? 25 : 38,
      partial: { ticker: "DEMO", name: "Demo company (simulated live job: tables arriving first)", sections: polls < 2 ? {} :
        { snapshot: lt.sections.snapshot, trajectory: lt.sections.trajectory, balance_sheet: lt.sections.balance_sheet, cash_quality: lt.sections.cash_quality }, states: [] } } });
  }
  return route.fulfill({ status: 404, json: {} });
});
await p.goto(`${BASE}/#settings`);
await p.evaluate(() => localStorage.setItem("finn.api", JSON.stringify("https://finn-api.test")));
await p.goto(`${BASE}/#research/DEMO`); await p.waitForTimeout(4200);
await shot(p, "14-research-cold-start", false);
await p.evaluate(() => localStorage.removeItem("finn.api"));
await p.close();

// 5. Alerts: default rule, then a noisy rule
p = await fresh("alerts");
await shot(p, "15-alerts-default"); await audit(p, "alerts");
await p.locator("#z").fill("2");
await p.getByRole("button", { name: /Volume condition/ }).click();
await shot(p, "16-alerts-noisy-rule", false);
await p.close();

// 6. Settings
p = await fresh("settings");
await shot(p, "17-settings"); await audit(p, "settings");
await p.close();

// 7. Desktop width (phone column centred)
const desk = await browser.newContext({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 1, colorScheme: "dark" });
const dp = await desk.newPage();
await dp.goto(`${BASE}/#brief`); await dp.waitForLoadState("networkidle"); await dp.waitForTimeout(900);
await dp.screenshot({ path: `${OUT}18-desktop-brief.png` }); shots.push("18-desktop-brief");

// PWA basics
const pwa = await (async () => {
  const pg = await ctx.newPage();
  await pg.goto(BASE); await pg.waitForTimeout(1500);
  const manifest = await (await fetch(`${BASE}/manifest.webmanifest`)).json();
  const sw = await pg.evaluate(async () => (await navigator.serviceWorker.getRegistration())?.active?.state || "none");
  return { manifest_name: manifest.name, icons: manifest.icons.length, display: manifest.display, service_worker: sw };
})();

await browser.close();
server.kill();
const report = { screenshots: shots, console_errors: errors, axe, pwa };
writeFileSync(`${OUT}report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
process.exit(0);
