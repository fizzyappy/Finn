import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { SwipeCard, ReactionChip } from "../cards/cards";
import { Cite, Icon, Ring } from "../components/ui";
import { api, backendAlive, briefForRange, catLabel, cleanTitle, fmtDay, fmtWhen, Json, prefs, sameText, snapshot, tidy, WindowKey, WINDOWS } from "../lib/data";

const HERO = 0.6, ONE = 0.3;
const plural = (n: number, word: string) => (n === 1 ? word : `${word}s`);
const clampTune = (v: number) => Math.min(1.5, Math.max(0.5, v));

/** Re-rank with the investor's swipes: score x tune(category), thresholds re-applied. */
function rerank(brief: Json, tune: Record<string, number>) {
  const events = [...(brief.hero || []), ...(brief.one_liners || [])].map((e: Json) => {
    const t = tune[e.category] ?? 1;
    const score = Math.min(1, e.score * t);
    return { ...e, base_score: e.score, score, tuned: t, treatment: score >= HERO ? "hero" : score >= ONE ? "one_liner" : "collapsed" };
  });
  const hero = events.filter((e) => e.treatment === "hero").sort((a, b) => b.score - a.score);
  const one = events.filter((e) => e.treatment === "one_liner").sort((a, b) => b.score - a.score);
  const demoted = events.filter((e) => e.treatment === "collapsed");
  return { hero, one, demoted };
}

function RangePicker({ min, max, initial, onApply, onCancel }: {
  min: string; max: string; initial: { from: string; to: string } | null;
  onApply: (from: string, to: string) => void; onCancel: () => void;
}) {
  const daysAgo = (n: number) => {
    const d = new Date(max); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10);
  };
  const [from, setFrom] = useState(initial?.from || daysAgo(4));
  const [to, setTo] = useState(initial?.to || max);
  const valid = from && to && from <= to;
  return (
    <div>
      <div className="h2" style={{ marginBottom: 10 }}>Pick a date range</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <label className="small muted">From
          <input className="field" type="date" value={from} max={to || max} onChange={(e) => setFrom(e.target.value)} style={{ marginTop: 4 }} />
        </label>
        <label className="small muted">To
          <input className="field" type="date" value={to} min={from} max={max} onChange={(e) => setTo(e.target.value)} style={{ marginTop: 4 }} />
        </label>
      </div>
      <div className="chips" style={{ marginTop: 10 }}>
        <button className="chip" onClick={() => { setFrom(max); setTo(max); }}>Today</button>
        <button className="chip" onClick={() => { setFrom(daysAgo(4)); setTo(max); }}>Last 5 days</button>
        <button className="chip" onClick={() => { setFrom(daysAgo(13)); setTo(max); }}>Last 14 days</button>
        <button className="chip" onClick={() => { setFrom(daysAgo(29)); setTo(max); }}>Last 30 days</button>
      </div>
      <p className="faint small">Built-in data covers {min} to {max}; older dates use the live research engine when it is connected.</p>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn small" disabled={!valid} onClick={() => valid && onApply(from, to)}>Show this range</button>
        <button className="btn secondary small" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function Brief({ onOpenResearch }: { onOpenResearch: (t: string) => void }) {
  const reduce = useReducedMotion();
  // First visit: there is no "last look" yet, so open on the last 24 hours.
  const [win, setWin] = useState<WindowKey>(() => (prefs.lastLook() ? "since_last_look" : "24h"));
  useEffect(() => { prefs.setLastLook(new Date().toISOString()); }, []);
  const [briefs, setBriefs] = useState<Record<string, Json>>({});
  const [err, setErr] = useState<string | null>(null);
  const [cleared, setCleared] = useState<Set<string>>(() => prefs.cleared());
  const [tune, setTune] = useState<Record<string, number>>(() => prefs.tune());
  const [openCat, setOpenCat] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  useEffect(() => () => { if ("speechSynthesis" in window) window.speechSynthesis.cancel(); }, []);

  const [range, setRange] = useState<{ from: string; to: string } | null>(null);
  const [picking, setPicking] = useState(false);
  const [live, setLive] = useState<Json | null>(null);
  const [liveNote, setLiveNote] = useState<string | null>(null);

  useEffect(() => {
    // Load every window at once so switching re-ranks instantly.
    Promise.all(WINDOWS.map((w) => snapshot(w.file).then((b) => [w.key, b] as const)))
      .then((pairs) => setBriefs(Object.fromEntries(pairs)))
      .catch((e) => setErr(String(e)));
  }, []);
  useEffect(() => { prefs.setCleared(cleared); }, [cleared]);
  useEffect(() => { prefs.setTune(tune); }, [tune]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2400); return () => clearTimeout(t); }, [toast]);

  const base14 = briefs["custom"];
  const minDay = base14?.window?.from?.slice(0, 10) || "";
  const maxDay = base14?.generated_at?.slice(0, 10) || "";
  const requested = win === "custom" && live ? live
    : win === "custom" && range && base14 ? briefForRange(base14, range.from, range.to) : briefs[win];
  // A quiet window never shows an empty screen: fall forward to the shortest window that has something.
  const { brief, quietLabel } = useMemo(() => {
    if (!requested) return { brief: requested, quietLabel: null as string | null };
    const heroes = (b: Json) => rerank(b, tune).hero.length > 0;
    const any = (b: Json) => { const r = rerank(b, tune); return r.hero.length + r.one.length > 0; };
    if (heroes(requested) || win === "custom") return { brief: requested, quietLabel: null };
    const order: WindowKey[] = ["since_last_look", "24h", "3d", "7d", "custom"];
    const later = order.slice(order.indexOf(win) + 1).filter((k) => briefs[k]);
    // Prefer the shortest window with something that needs attention; else one with anything worth knowing.
    const k = later.find((k) => heroes(briefs[k])) || (any(requested) ? undefined : later.find((k) => any(briefs[k])));
    return k ? { brief: briefs[k], quietLabel: requested.window.label as string } : { brief: requested, quietLabel: null };
  }, [requested, briefs, tune, win]);
  const ranked = useMemo(() => (brief ? rerank(brief, tune) : null), [brief, tune]);

  const applyRange = async (from: string, to: string) => {
    setPicking(false); setLive(null); setLiveNote(null);
    setRange({ from, to }); setWin("custom");
    if (from < minDay) {
      // Older than the built-in data: ask the live backend, if there is one.
      if (await backendAlive(4000)) {
        try {
          setLiveNote("Fetching that range from the research engine…");
          setLive(await api(`/brief?start=${from}T00:00:00%2B05:30&end=${to}T23:59:59%2B05:30`, undefined, 120000));
          setLiveNote(null);
        } catch { setLiveNote(`Could not fetch the range before ${minDay}; showing what the built-in data covers.`); }
      } else {
        setLiveNote(`The built-in data starts ${minDay}; connect the backend in Settings for older dates.`);
      }
    }
  };
  if (err) return <div className="glass card notice">Could not load the brief: {err}</div>;
  if (!brief || !ranked) return <div className="faint" style={{ padding: 40, textAlign: "center" }}>Loading your brief…</div>;

  const id = (e: Json) => `${e.symbol}|${e.uid || e.ts}`;
  const heroLeft = ranked.hero.filter((e) => !cleared.has(id(e)));
  const heroDone = ranked.hero.length - heroLeft.length;
  const matter = ranked.hero.length + ranked.one.length;
  const collapsed: Record<string, Json> = brief.collapsed || {};
  const routine = Object.values(collapsed).reduce((a: number, c: Json) => a + c.count, 0);

  const onScreen = new Set([...ranked.hero, ...ranked.one].map(id));
  const all14 = base14 ? [...(base14.hero || []), ...(base14.one_liners || [])] : [];
  const latestResults = all14
    .filter((e: Json) => e.card_kind === "results" && !onScreen.has(id(e)) && !cleared.has(id(e)))
    .sort((a: Json, b: Json) => (b.ts || "").localeCompare(a.ts || ""))
    .slice(0, 3);

  const clear = (e: Json) => setCleared((s) => new Set(s).add(id(e)));
  const less = (e: Json) => {
    const next = clampTune((tune[e.category] ?? 1) * 0.8);
    setTune({ ...tune, [e.category]: next });
    setToast(`Less ${catLabel(e.category)} from now on (×${next.toFixed(2)}). Undo in Settings.`);
  };
  /** "Play my brief": the cards that need attention, read in about a minute (≈150 words). */
  const playBrief = () => {
    if (!("speechSynthesis" in window)) { setToast("This browser can't read aloud."); return; }
    const synth = window.speechSynthesis;
    if (playing) { synth.cancel(); setPlaying(false); return; }
    const intro = heroLeft.length
      ? `${heroLeft.length} ${plural(heroLeft.length, "thing")} need your attention.`
      : `Nothing needs your attention. ${matter} ${plural(matter, "item")} worth knowing.`;
    const parts = [intro];
    let words = intro.split(" ").length;
    for (const e of heroLeft) {
      const line = `${e.symbol}: ${tidy(e.summary?.headline || e.subject).replace(/₹([\d,.]+) cr/g, "$1 crore rupees").replace(/₹/g, "rupees ")}.`;
      if (words + line.split(" ").length > 150) break;
      parts.push(line);
      words += line.split(" ").length;
    }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(parts.join(" "));
    u.lang = "en-IN";
    u.rate = 1.0;
    u.onend = () => setPlaying(false);
    u.onerror = () => setPlaying(false);
    setPlaying(true);
    synth.speak(u);
  };

  return (
    <div>
      <div className="brief-head">
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 className="h1">{win === "custom" && range ? brief.window.label : "Your brief"}</h1>
          <div className="counts tnum">
            <b>{matter}</b> matter · <b>{heroLeft.length}</b> to clear · {brief.header.filings} {plural(brief.header.filings, "filing")}
          </div>
        </div>
        {ranked.hero.length > 0 && <Ring done={heroDone} total={ranked.hero.length} />}
        {matter > 0 && <button className={`icon-btn ${playing ? "on" : ""}`} onClick={playBrief} aria-pressed={playing}
          aria-label={playing ? "Stop reading" : "Play my brief (about a minute)"} title={playing ? "Stop" : "Play my brief"}>
          {playing ? <span className="stop-sq" aria-hidden /> : Icon.speaker}
        </button>}
      </div>

      <div className="chips" role="toolbar" aria-label="Time window">
        {WINDOWS.map((w) => (
          <button key={w.key} className="chip" aria-pressed={w.key === win}
            onClick={() => (w.key === "custom" ? setPicking((p) => !p) : (setWin(w.key), setPicking(false)))}
            aria-expanded={w.key === "custom" ? picking : undefined}>
            {w.key === "custom" && range && win === "custom" ? brief.window.label : w.label}
          </button>
        ))}
      </div>
      <AnimatePresence initial={false}>
        {picking && base14 && (
          <motion.div className="glass card" style={{ marginTop: 10 }} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
            <RangePicker min={minDay} max={maxDay} initial={range} onApply={applyRange} onCancel={() => setPicking(false)} />
          </motion.div>
        )}
      </AnimatePresence>
      {liveNote && win === "custom" && <div className="notice" style={{ marginTop: 10 }}>{liveNote}</div>}
      {quietLabel && (
        <div className="small muted" style={{ margin: "10px 2px 0" }}>
          Nothing urgent {/^since/.test(quietLabel) ? quietLabel.replace("since you last looked", "since your last look") : `in the ${quietLabel}`}. Showing the {brief.window.label}.
        </div>
      )}

      {ranked.hero.length === 0 && ranked.one.length === 0 ? (
        <div className="glass card empty" style={{ marginTop: 14 }}>
          <div className="big">Quiet {brief.window.label}</div>
          <div className="muted">Nothing material across your {brief.holdings.length} holdings.{routine ? ` ${routine} routine ${plural(routine, "filing")} collapsed below.` : ""}</div>
        </div>
      ) : ranked.hero.length === 0 ? null : (
        <>
          <div className="section-title"><h2>Needs your attention</h2><span className="meta">tap Why? · swipe → to clear</span></div>
          <AnimatePresence initial={false} mode="popLayout">
            {heroLeft.map((e) => (
              <motion.div key={id(e)} layout={!reduce} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 0, scale: 0.96, transition: { duration: 0.18 } }} transition={{ type: "spring", stiffness: 300, damping: 30 }}>
                <SwipeCard e={e} onClear={() => clear(e)} onLess={() => { less(e); clear(e); }} />
              </motion.div>
            ))}
          </AnimatePresence>
          {heroLeft.length === 0 && ranked.hero.length > 0 && (
            <motion.div className="glass card empty hero-glow" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}>
              <svg width="54" height="54" viewBox="0 0 54 54" aria-hidden>
                <circle cx="27" cy="27" r="25" fill="rgba(124,242,154,0.14)" stroke="var(--mint)" strokeWidth="2" />
                <motion.path d="M16 28l7 7 15-16" fill="none" stroke="var(--mint)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.5, delay: 0.1 }} />
              </svg>
              <div className="big">You're clear</div>
              <div className="muted">FINN kept {ranked.one.length} one-liners and {routine} routine filings out of your way.</div>
              <button className="btn secondary small" style={{ marginTop: 14 }} onClick={() => setCleared(new Set())}>Bring cards back</button>
            </motion.div>
          )}
        </>
      )}

      {latestResults.length > 0 && (
        <>
          <div className="section-title"><h2>Latest results</h2><span className="meta">last 14 days</span></div>
          {latestResults.map((e: Json) => (
            <div key={id(e)} style={{ marginBottom: 12 }}>
              <SwipeCard e={e} onClear={() => clear(e)} onLess={() => { less(e); clear(e); }} />
            </div>
          ))}
        </>
      )}

      {ranked.one.length > 0 && (
        <>
          <div className="section-title"><h2>Worth knowing</h2><span className="meta">{ranked.one.length}</span></div>
          <div className="glass row-list">
            {ranked.one.map((e) => (
              <div className="row" key={id(e)}>
                <div className="grow">
                  <div className="sym-line">{e.symbol}</div>
                  <div className="title">{tidy(e.summary?.headline || e.subject)}</div>
                  {e.summary?.one_liner && !sameText(e.summary.one_liner, e.summary.headline) && <div className="desc">{tidy(e.summary.one_liner)}</div>}
                  <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                    <span className="tag">{catLabel(e.category)}</span>
                    <ReactionChip r={e.reaction} ts={e.ts} />
                    {e.url && <Cite href={e.url}>Filing ↗</Cite>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {brief.alerts?.length > 0 && (
        <>
          <div className="section-title"><h2>Unusual moves</h2><span className="meta">rule: notable move</span></div>
          <div className="glass row-list">
            {brief.alerts.slice(0, 4).map((a: Json) => (
              <div className="row" key={a.symbol + a.date}>
                <div className="grow">
                  <div className="title tnum">
                    {a.symbol} <span className={a.measures.ret_pct > 0 ? "up" : "down"}>{a.measures.ret_pct > 0 ? "+" : ""}{a.measures.ret_pct}%</span>
                    <span className="faint small"> · {fmtDay(a.date)}</span>
                  </div>
                  <div className="desc">A move {Math.abs(a.measures.z).toFixed(1)}× its usual daily move (Nifty {a.measures.mkt_ret_pct > 0 ? "+" : ""}{a.measures.mkt_ret_pct}%), on {Number(a.measures.vol_x).toFixed(1)}× its usual volume</div>
                  {a.filed_before?.length > 0 && <div className="desc" style={{ color: "var(--mint-2)" }}>Filed before this move: {cleanTitle(a.filed_before[0].title)}</div>}
                </div>
                <button className="why-btn" onClick={() => onOpenResearch(a.symbol)}>Research</button>
              </div>
            ))}
          </div>
        </>
      )}

      {(routine > 0 || ranked.demoted.length > 0) && <>
      <div className="section-title"><h2>Collapsed</h2><span className="meta">{routine} routine</span></div>
      <div className="glass">
        {Object.entries(collapsed).map(([cat, c]: [string, Json]) => (
          <div key={cat}>
            <button className="collapsed-cat" onClick={() => setOpenCat(openCat === cat ? null : cat)} aria-expanded={openCat === cat}>
              <span>{catLabel(cat)}</span><span className="count-pill">{c.count}</span>
            </button>
            <AnimatePresence initial={false}>
              {openCat === cat && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden" }}>
                  {c.items.slice(0, 12).map((it: Json, i: number) => (
                    <div key={i} className="small" style={{ padding: "6px 16px", color: "var(--text-2)", display: "flex", gap: 8 }}>
                      <b style={{ color: "var(--text)", minWidth: 74 }}>{it.symbol}</b>
                      <span style={{ flex: 1 }}>{cleanTitle(it.title)}</span>
                      <span className="faint">{fmtWhen(it.ts)}</span>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
        {ranked.demoted.length > 0 && (
          <div className="collapsed-cat faint"><span>moved down by your swipes</span><span className="count-pill">{ranked.demoted.length}</span></div>
        )}
      </div>
      </>}
      <p className="faint small" style={{ margin: "14px 4px" }}>
        Sources: exchange filings (BSE/NSE feeds) and Screener · updated {fmtWhen(brief.generated_at)}
      </p>

      <div style={{ position: "fixed", left: 0, right: 0, bottom: "calc(var(--safe-bottom) + 84px)", display: "flex", justifyContent: "center", zIndex: 30, pointerEvents: "none" }}>
        <AnimatePresence>
          {toast && (
            <motion.div role="status" className="glass" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
              style={{ padding: "10px 16px", fontSize: 13, maxWidth: "88vw" }}>
              {toast}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
