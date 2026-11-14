import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { SwipeCard, ReactionChip } from "../cards/cards";
import { Cite, Icon, Ring } from "../components/ui";
import { cleanTitle, fmtDay, fmtWhen, Json, nice, prefs, snapshot, WindowKey, WINDOWS } from "../lib/data";

const HERO = 0.6, ONE = 0.3;
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

export default function Brief({ onOpenResearch }: { onOpenResearch: (t: string) => void }) {
  const reduce = useReducedMotion();
  const [win, setWin] = useState<WindowKey>("since_last_look");
  const [briefs, setBriefs] = useState<Record<string, Json>>({});
  const [err, setErr] = useState<string | null>(null);
  const [cleared, setCleared] = useState<Set<string>>(() => prefs.cleared());
  const [tune, setTune] = useState<Record<string, number>>(() => prefs.tune());
  const [openCat, setOpenCat] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    // Load every window at once so switching re-ranks instantly.
    Promise.all(WINDOWS.map((w) => snapshot(`brief_${w.key}.json`).then((b) => [w.key, b] as const)))
      .then((pairs) => setBriefs(Object.fromEntries(pairs)))
      .catch((e) => setErr(String(e)));
  }, []);
  useEffect(() => { prefs.setCleared(cleared); }, [cleared]);
  useEffect(() => { prefs.setTune(tune); }, [tune]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2400); return () => clearTimeout(t); }, [toast]);

  const brief = briefs[win];
  const ranked = useMemo(() => (brief ? rerank(brief, tune) : null), [brief, tune]);
  if (err) return <div className="glass card notice">Could not load the brief: {err}</div>;
  if (!brief || !ranked) return <div className="faint" style={{ padding: 40, textAlign: "center" }}>Loading your brief…</div>;

  const id = (e: Json) => `${e.symbol}|${e.uid || e.ts}`;
  const heroLeft = ranked.hero.filter((e) => !cleared.has(id(e)));
  const heroDone = ranked.hero.length - heroLeft.length;
  const matter = ranked.hero.length + ranked.one.length;
  const collapsed: Record<string, Json> = brief.collapsed || {};
  const routine = Object.values(collapsed).reduce((a: number, c: Json) => a + c.count, 0);

  const clear = (e: Json) => setCleared((s) => new Set(s).add(id(e)));
  const less = (e: Json) => {
    const next = clampTune((tune[e.category] ?? 1) * 0.8);
    setTune({ ...tune, [e.category]: next });
    setToast(`Less ${nice(e.category)} from now on (×${next.toFixed(2)}). Undo in Settings.`);
  };
  const readAloud = () => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const lines = [`${brief.header.filings} filings, ${matter} matter.`,
      ...heroLeft.map((e: Json) => `${e.symbol}. ${e.summary?.headline || e.subject}.`),
      ...ranked.one.slice(0, 5).map((e: Json) => `${e.symbol}. ${e.summary?.one_liner || e.summary?.headline || ""}`)];
    const u = new SpeechSynthesisUtterance(lines.join(" "));
    u.lang = "en-IN";
    u.rate = 1.02;
    window.speechSynthesis.speak(u);
  };

  return (
    <div>
      <div className="brief-head">
        <Ring done={heroDone} total={ranked.hero.length} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 className="h1">{win === "since_last_look" ? "Since you last looked" : `Your ${brief.window.label.replace("last ", "last ")}`}</h1>
          <div className="counts tnum">
            <b>{brief.header.filings}</b> filings · <b>{matter}</b> matter · <b>{heroLeft.length}</b> left
            {brief.alerts?.length ? <> · <b>{brief.alerts.length}</b> moves</> : null}
          </div>
        </div>
        <button className="why-btn" onClick={readAloud} aria-label="Read the brief aloud" style={{ height: 40, width: 40, padding: 0, display: "grid", placeItems: "center" }}>{Icon.speaker}</button>
      </div>

      <div className="chips" role="toolbar" aria-label="Time window">
        {WINDOWS.map((w) => (
          <button key={w.key} className="chip" aria-pressed={w.key === win} onClick={() => setWin(w.key)}>{w.label}</button>
        ))}
      </div>

      {brief.quiet && ranked.hero.length === 0 ? (
        <div className="glass card empty" style={{ marginTop: 14 }}>
          <img src="/icons/finn.svg" width={54} height={54} alt="" style={{ borderRadius: 16 }} />
          <div className="big">Quiet {brief.window.label}</div>
          <div className="muted">Nothing material across your {brief.holdings.length} holdings.{routine ? ` ${routine} routine filings collapsed below.` : ""}</div>
        </div>
      ) : (
        <>
          <div className="section-title"><h2>Needs your attention</h2><span className="meta">swipe → to clear</span></div>
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

      {ranked.one.length > 0 && (
        <>
          <div className="section-title"><h2>Worth knowing</h2><span className="meta">{ranked.one.length}</span></div>
          <div className="glass row-list">
            {ranked.one.map((e) => (
              <div className="row" key={id(e)}>
                <div className="ticker-badge" aria-hidden>{e.symbol.slice(0, 4)}</div>
                <div className="grow">
                  <div className="title">{e.summary?.headline || e.subject}</div>
                  {e.summary?.one_liner && <div className="desc">{e.summary.one_liner}</div>}
                  <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                    <span className="tag">{nice(e.category)}</span>
                    <ReactionChip r={e.reaction} ts={e.ts} />
                    {e.url && <Cite href={e.url}>filing</Cite>}
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
                <div className="ticker-badge" aria-hidden>{a.symbol.slice(0, 4)}</div>
                <div className="grow">
                  <div className="title tnum">
                    {a.symbol} <span className={a.measures.ret_pct > 0 ? "up" : "down"}>{a.measures.ret_pct > 0 ? "+" : ""}{a.measures.ret_pct}%</span>
                    <span className="faint small"> · {fmtDay(a.date)}</span>
                  </div>
                  <div className="desc">{Math.abs(a.measures.z).toFixed(1)}× its normal day after the market · volume {a.measures.vol_x}× average</div>
                  {a.filed_before?.length > 0 && <div className="desc" style={{ color: "var(--mint-2)" }}>Filed before this move: {cleanTitle(a.filed_before[0].title)}</div>}
                </div>
                <button className="why-btn" onClick={() => onOpenResearch(a.symbol)}>Research</button>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="section-title"><h2>Collapsed</h2><span className="meta">{routine} routine</span></div>
      <div className="glass">
        {Object.entries(collapsed).map(([cat, c]: [string, Json]) => (
          <div key={cat}>
            <button className="collapsed-cat" onClick={() => setOpenCat(openCat === cat ? null : cat)} aria-expanded={openCat === cat}>
              <span>{nice(cat)}</span><span className="count-pill">{c.count}</span>
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
      <p className="faint small" style={{ margin: "14px 4px" }}>
        Data as of {fmtWhen(brief.generated_at)}. {brief.data_status?.filings_note}
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
