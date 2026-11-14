// Render the SVG logo to PNG icons with the installed Chrome (no browser download).
import { chromium } from "playwright-core";
import { readFileSync } from "node:fs";

const svg = readFileSync(new URL("../public/icons/finn.svg", import.meta.url), "utf8");
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage();
for (const [size, name, pad] of [[180, "icon-180.png", 0], [192, "icon-192.png", 0], [512, "icon-512.png", 0], [512, "icon-maskable-512.png", 0.12]]) {
  await page.setViewportSize({ width: size, height: size });
  const inner = Math.round(size * (1 - pad * 2));
  await page.setContent(`<html><body style="margin:0;background:#06120D;display:grid;place-items:center;width:${size}px;height:${size}px">
    <div style="width:${inner}px;height:${inner}px">${svg.replace("<svg ", `<svg width="${inner}" height="${inner}" `)}</div></body></html>`);
  await page.screenshot({ path: new URL(`../public/icons/${name}`, import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1") });
}
await browser.close();
console.log("icons written");
