// Data: a frozen snapshot of real outputs ships inside the app (always works), and a
// live FastAPI backend is used when one is configured and reachable.

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Json = any;

export type WindowKey = "since_last_look" | "24h" | "3d" | "7d" | "custom";
export const WINDOWS: { key: WindowKey; label: string; file: string }[] = [
  { key: "since_last_look", label: "Since last look", file: "brief_since_last_look.json" },
  { key: "24h", label: "24h", file: "brief_24h.json" },
  { key: "3d", label: "3 days", file: "brief_3d.json" },
  { key: "7d", label: "7 days", file: "brief_7d.json" },
  { key: "custom", label: "Custom", file: "brief_14d.json" },     // any range inside the last 14 days
];

/** A brief narrowed to [from, to] (YYYY-MM-DD, inclusive), computed on the device. */
export function briefForRange(base: Json, from: string, to: string): Json {
  const inRange = (ts?: string) => !!ts && ts.slice(0, 10) >= from && ts.slice(0, 10) <= to;
  const hero = (base.hero || []).filter((e: Json) => inRange(e.ts));
  const one = (base.one_liners || []).filter((e: Json) => inRange(e.ts));
  const collapsed: Record<string, Json> = {};
  for (const [cat, c] of Object.entries<Json>(base.collapsed || {})) {
    const items = (c.items || []).filter((it: Json) => inRange(it.ts));
    if (items.length) collapsed[cat] = { count: items.length, items };
  }
  const alerts = (base.alerts || []).filter((a: Json) => a.date >= from && a.date <= to);
  const filings = [...hero, ...one].reduce((n: number, e: Json) => n + 1 + (e.related?.length || 0), 0)
    + Object.values(collapsed).reduce((n: number, c: Json) => n + c.count, 0);
  const fmt = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return {
    ...base, hero, one_liners: one, collapsed, alerts,
    quiet: hero.length === 0 && alerts.length === 0,
    window: { label: from === to ? fmt(from) : `${fmt(from)} – ${fmt(to)}`, from, to },
    header: { ...base.header, filings, matter: hero.length + one.length, hero: hero.length, alerts: alerts.length },
  };
}

const cache = new Map<string, Promise<Json>>();

export function snapshot(path: string): Promise<Json> {
  if (!cache.has(path)) {
    cache.set(path, fetch(`/data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    }).catch((e) => { cache.delete(path); throw e; }));
  }
  return cache.get(path)!;
}

// ---------------------------------------------------------------- local prefs
function read<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
}
function write(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: keep in memory only */ }
}
export const prefs = {
  // On this PC the local backend is found automatically; elsewhere it is set in Settings.
  // Backend URL: a value saved in Settings wins; else the one baked in at build time
  // (VITE_API_BASE, e.g. the Render URL); else the local backend when run on this PC.
  apiBase: () => {
    const v = read<string>("finn.api", "");
    if (v === "off") return "";                 // explicitly offline: snapshot only
    const built = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/+$/, "") || "";
    return v || built || (location.hostname === "localhost" ? "http://localhost:8000" : "");
  },
  setApiBase: (v: string) => write("finn.api", v.trim().replace(/\/+$/, "")),
  cleared: () => new Set(read<string[]>("finn.cleared", [])),
  setCleared: (s: Set<string>) => write("finn.cleared", [...s]),
  tune: () => read<Record<string, number>>("finn.tune", {}),
  setTune: (t: Record<string, number>) => write("finn.tune", t),
  lastLook: () => read<string | null>("finn.lastlook", null),
  setLastLook: (v: string) => write("finn.lastlook", v),
};

// ---------------------------------------------------------------- live API
export async function api(path: string, init?: RequestInit, timeoutMs = 8000): Promise<Json> {
  const base = prefs.apiBase();
  if (!base) throw new Error("no backend configured");
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(`${base}${path}`, { ...init, signal: ctl.signal });
    if (!r.ok) throw new Error(`${r.status} ${await r.text().catch(() => "")}`.slice(0, 200));
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

export async function backendAlive(timeoutMs = 3000): Promise<boolean> {
  try {
    const r = await api("/health", undefined, timeoutMs);
    return !!r?.ok;
  } catch {
    return false;
  }
}

/** A free cloud server sleeps when idle and needs up to ~50 s to wake. Quick check
 *  first; if that fails, call onWaking() and keep trying for up to 75 s. */
export async function wakeBackend(onWaking: () => void): Promise<boolean> {
  if (!prefs.apiBase()) return false;
  if (await backendAlive(2500)) return true;
  onWaking();
  const until = Date.now() + 75000;
  while (Date.now() < until) {
    if (await backendAlive(20000)) return true;
    await new Promise((r) => setTimeout(r, 2000));
  }
  return false;
}

// ---------------------------------------------------------------- formatting
const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inr1 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });
export const fmtCr = (v?: number | null) =>
  v == null ? "–" : `₹${Math.abs(v) >= 100 ? inr.format(v) : inr1.format(v)} cr`;
export const fmtNum = (v?: number | null, d = 0) =>
  v == null ? "–" : new Intl.NumberFormat("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d }).format(v);
export const fmtPct = (v?: number | null, d = 1) => (v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(d)}%`);
export const signClass = (v?: number | null) => (v == null || v === 0 ? "" : v > 0 ? "up" : "down");
export function fmtWhen(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}
export function fmtDay(iso?: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
export const nice = (s?: string) => (s || "").replace(/_/g, " ");
/** Exchange subjects without the regulatory boilerplate prefix. */
export const cleanTitle = (s?: string) =>
  (s || "").replace(/^(announcement|intimation|disclosure)\s+under\s+regulation\s+\d+\s*(\(\w+\))?\s*(of .{0,40}?regulations?,? \d{4})?\s*[-:]?\s*/i, "").trim();
export const pageLink = (url?: string, page?: number) => (url ? (page ? `${url}#page=${page}` : url) : undefined);
