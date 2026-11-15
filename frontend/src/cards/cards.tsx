import { AnimatePresence, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useRef, useState } from "react";
import { Cite, CountUp, Icon } from "../components/ui";
import { catLabel, fmtNum, fmtPct, fmtWhen, Json, metricLabel, monthYear, nice, pageLink, sameText, signClass, tidy } from "../lib/data";

/* ---------------------------------------------------------------- shared bits */
export function Who({ e }: { e: Json }) {
  return (
    <div className="who">
      <div style={{ minWidth: 0 }}>
        <div className="name"><span className="ticker-chip">{e.symbol}</span></div>
        <div className="sub">{catLabel(e.category)} · {fmtWhen(e.ts)}</div>
      </div>
    </div>
  );
}

export function ReactionChip({ r, ts }: { r: Json; ts?: string }) {
  if (!r || (Math.abs(r.z || 0) < 1.5 && (r.vol_x || 0) < 1.5)) return null;
  const sameDay = ts && r.date === ts.slice(0, 10);
  const parts = [Math.abs(r.z) >= 1.5 ? `${Math.abs(r.z).toFixed(1)}× usual move` : null,
    r.vol_x >= 1.5 ? `${r.vol_x.toFixed(1)}× vol` : null, sameDay ? "same day" : "next day"].filter(Boolean);
  return (
    <span className={`tag ${Math.abs(r.z) >= 2 ? "mint" : ""}`}
      title={`How the stock traded ${sameDay ? "the day of" : "the day after"} this filing (the filing came first)`}>
      <span className={signClass(r.ret_pct)}>{fmtPct(r.ret_pct)}</span>{" · "}{parts.join(" · ")}
    </span>
  );
}

/* ---------------------------------------------------------------- results card */
const METRIC_LABEL: Record<string, string> = {
  revenue: "Revenue", ebitda: "EBITDA", pbt: "PBT", pat: "PAT", net_interest_income: "NII",
  operating_profit_before_provisions: "Op. profit", provisions: "Provisions",
};

export function ResultsBody({ e }: { e: Json }) {
  const c = e.card || {};
  const m = c.metrics || {};
  const [showChecks, setShowChecks] = useState(false);
  const rows = ["revenue", "net_interest_income", "operating_profit_before_provisions", "ebitda", "pbt", "pat", "provisions"]
    .filter((k) => m[k]);
  const cmp = c.compare_label || "QoQ";
  return (
    <div>
      <div className="headline">{tidy(e.summary?.headline)}</div>
      <table className="metrics">
        <thead>
          <tr><th>{c.period_type === "half_year" ? "Half-year" : "Quarter"} · ₹ cr</th><th>Value</th><th>{cmp === "QoQ" ? "QoQ" : "vs H-1"}</th><th>YoY</th></tr>
        </thead>
        <tbody>
          {rows.map((k) => (
            <tr key={k}>
              <td>{METRIC_LABEL[k]}{k === "ebitda" ? <span className="faint small"> (derived)</span> : null}</td>
              <td className="big"><CountUp value={m[k].value} format={(v) => fmtNum(v, Math.abs(m[k].value) < 100 ? 1 : 0)} /></td>
              <td className={signClass(m[k].qoq_pct)}>{m[k].qoq_pct != null ? fmtPct(m[k].qoq_pct) : <span className="faint small">{m[k].qoq_note || "–"}</span>}</td>
              <td className={signClass(m[k].yoy_pct)}>{m[k].yoy_pct != null ? fmtPct(m[k].yoy_pct) : <span className="faint small">{m[k].yoy_note || "–"}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {m.ebitda_margin_pct && (
        <div className="small muted" style={{ marginTop: 8 }}>
          EBITDA margin <b className="tnum" style={{ color: "var(--text)" }}>{m.ebitda_margin_pct.value}%</b>
          {m.ebitda_margin_pct.change_bps_yoy != null && <span className={signClass(m.ebitda_margin_pct.change_bps_yoy)}> ({m.ebitda_margin_pct.change_bps_yoy > 0 ? "+" : ""}{m.ebitda_margin_pct.change_bps_yoy} bps YoY)</span>}
        </div>
      )}
      {(c.vs_guidance || []).slice(0, 2).map((g: Json, i: number) => (
        <div key={i} className="small" style={{ marginTop: 8, color: "var(--mint-2)" }}>
          vs guidance: {metricLabel(g.metric)} {g.horizon} target {g.target} <span className="faint">(said {monthYear(g.said_on)})</span>
        </div>
      ))}
      <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        {c.status === "verified" ? (
          <button className="verified" onClick={(ev) => { ev.stopPropagation(); setShowChecks((s) => !s); }} aria-expanded={showChecks}>
            {Icon.check} Verified · {c.checks?.filter((x: Json) => x.ok).length}/{c.checks?.length} checks
          </button>
        ) : (
          <span className="tag amber">Not verified: open the filing</span>
        )}
        <span className="faint small">{c.basis} · numbers read from the filing, checked by Python</span>
      </div>
      <AnimatePresence initial={false}>
        {showChecks && (
          <motion.ul className="checklist" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            {c.checks.map((x: Json) => (
              <li key={x.name}><span className={x.ok ? "ok" : "bad"}>{x.ok ? Icon.check : Icon.cross}</span><span><b style={{ color: "var(--text)" }}>{x.name}</b> · {x.detail}</span></li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ---------------------------------------------------------------- people card */
export function PeopleBody({ e }: { e: Json }) {
  const c = e.card || {};
  return (
    <div>
      <div className="headline">{tidy(c.headline || e.summary?.headline)}</div>
      {(c.people || []).slice(0, 3).map((p: Json) => (
        <div className="person" key={p.name}>
          <div className="pname">{p.name} <span className="faint small">· {p.role}</span></div>
          <div className="small muted">{nice(p.change)}{p.effective_date ? ` · effective ${p.effective_date}` : ""}</div>
          {p.reason && <div className="small faint">Reason: {p.reason}</div>}
          <ul className="career">
            {(p.background || []).slice(0, 3).map((b: Json, i: number) => (
              <li key={i}>{b.text} <Cite href={pageLink(c.source_url, b.page)}>filing p.{b.page}</Cite></li>
            ))}
          </ul>
        </div>
      ))}
      {c.dropped_unverified_lines > 0 && <div className="faint small">{c.dropped_unverified_lines} line(s) left out: not found word for word in the filing.</div>}
    </div>
  );
}

export function SummaryBody({ e }: { e: Json }) {
  return (
    <div>
      <div className="headline">{tidy(e.summary?.headline || e.subject)}</div>
      {e.summary?.one_liner && !sameText(e.summary.one_liner, e.summary.headline) && <div className="oneliner">{tidy(e.summary.one_liner)}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- the why (back face) */
export function WhyBody({ e, onBack }: { e: Json; onBack: () => void }) {
  return (
    <div>
      <div className="card-top">
        <div className="h2">Why you're seeing this</div>
        <button className="why-btn" onClick={(ev) => { ev.stopPropagation(); onBack(); }}>Back</button>
      </div>
      <div className="score-bar" aria-hidden><div style={{ width: `${Math.round(e.score * 100)}%` }} /></div>
      <div className="small muted" style={{ marginBottom: 6 }}>Score <b className="tnum" style={{ color: "var(--text)" }}>{e.score.toFixed(2)}</b> · cards from 0.60, one-liners from 0.30</div>
      <ul className="why-list">
        {e.score_parts.map((p: Json, i: number) => (
          <li key={i}>
            <span>{p.why}</span>
            <span className="v">{p.factor === "base" ? p.value.toFixed(2) : p.factor === "multiply" ? `×${p.value}` : p.factor === "add" ? `+${p.value}` : ""}</span>
          </li>
        ))}
        {e.tuned && e.tuned !== 1 && <li><span>your swipes on {catLabel(e.category)}</span><span className="v">×{e.tuned.toFixed(2)}</span></li>}
      </ul>
      <div className="faint small" style={{ marginTop: 8 }}>
        Classified by {e.class_method === "rule" ? "a rule" : "Gemini (rules were unsure)"} as {catLabel(e.category)} ({nice(e.subtype)}).
        {e.related?.length ? ` ${e.related.length} related filing(s) folded in.` : ""}
      </div>
      {e.url && <div style={{ marginTop: 10 }}><Cite href={e.url}>open the filing</Cite></div>}
    </div>
  );
}

/* ---------------------------------------------------------------- swipe + flip */
/** The face that is turned away can't be reached by keyboard or screen reader. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const hidden = (h: boolean): any => (h ? { inert: "" } : {});

export function SwipeCard({ e, onClear, onLess }: { e: Json; onClear: () => void; onLess: () => void }) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-220, 0, 220], reduce ? [0, 0, 0] : [-6, 0, 6]);
  const rightOp = useTransform(x, [20, 110], [0, 1]);
  const leftOp = useTransform(x, [-110, -20], [1, 0]);
  const [flipped, setFlipped] = useState(false);
  const press = useRef<number | null>(null);
  const moved = useRef(false);
  const kind = e.card?.type === "results" && e.card?.status !== "failed" ? "results" : e.card?.type === "people" && e.card?.people?.length ? "people" : "summary";

  const startPress = () => {
    moved.current = false;
    press.current = window.setTimeout(() => { if (!moved.current) setFlipped((f) => !f); }, 520);
  };
  const endPress = () => { if (press.current) window.clearTimeout(press.current); press.current = null; };

  return (
    <div className="swipe-wrap" style={{ marginBottom: 12 }}>
      <motion.div className="swipe-hint right" style={{ opacity: rightOp }} aria-hidden>✓ CLEAR</motion.div>
      <motion.div className="swipe-hint left" style={{ opacity: leftOp }} aria-hidden>LESS LIKE THIS</motion.div>
      <motion.div
        drag={flipped ? false : "x"} dragConstraints={{ left: 0, right: 0 }} dragElastic={0.9}
        style={{ x, rotate }}
        onDrag={(_, i) => { if (Math.abs(i.offset.x) > 8) { moved.current = true; endPress(); } }}
        onDragEnd={(_, i) => {
          if (i.offset.x > 110 || i.velocity.x > 700) onClear();
          else if (i.offset.x < -110 || i.velocity.x < -700) onLess();
        }}
        onPointerDown={startPress} onPointerUp={endPress} onPointerCancel={endPress}
        whileTap={{ scale: 0.995 }}
      >
        <div className="flip-scene">
          <motion.div className="flip-inner" animate={{ rotateY: flipped ? 180 : 0 }}
            transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 260, damping: 26 }}>
            <article className={`glass card face ${e.score >= 0.75 ? "hero-glow" : ""}`} aria-hidden={flipped} {...hidden(flipped)}>
              <div className="card-top">
                <Who e={e} />
                <span className="tag ghost tnum" title="How much this matters to you, 0 to 1. Tap Why? for the breakdown.">score {e.score.toFixed(2)}</span>
              </div>
              {kind === "results" ? <ResultsBody e={e} /> : kind === "people" ? <PeopleBody e={e} /> : <SummaryBody e={e} />}
              <div className="card-foot">
                <div className="tags">
                  <ReactionChip r={e.reaction} ts={e.ts} />
                  {e.related?.length > 0 && <span className="tag">+{e.related.length} related</span>}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {e.url && <Cite href={e.url}>Filing ↗</Cite>}
                  <button className="why-btn" onClick={(ev) => { ev.stopPropagation(); setFlipped(true); }} aria-label={`Why am I seeing ${e.symbol}?`}>Why?</button>
                </div>
              </div>
              <div className="sr-only">
                <button onClick={onClear}>Clear this card</button>
                <button onClick={onLess}>Show less like this</button>
              </div>
            </article>
            <article className="glass card face back" aria-hidden={!flipped} {...hidden(!flipped)}>
              <WhyBody e={e} onBack={() => setFlipped(false)} />
            </article>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
