import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Cite } from "../components/ui";
import { cleanTitle, fmtDay, Json, snapshot } from "../lib/data";

type Row = [string, number, number | null, number | null, number | null, number, number];
const DAYS = 90;

export default function Alerts({ onOpenResearch }: { onOpenResearch: (t: string) => void }) {
  const [series, setSeries] = useState<Record<string, Row[]> | null>(null);
  const [recent, setRecent] = useState<Json[]>([]);
  const [who, setWho] = useState<string>("any holding");
  const [z, setZ] = useState(3.0);
  const [vol, setVol] = useState(2.5);
  const [useVol, setUseVol] = useState(true);

  useEffect(() => {
    snapshot("alert_series.json").then((d) => setSeries(d.series)).catch(() => setSeries({}));
    snapshot("brief_14d.json").then((b) => setRecent(b.alerts || [])).catch(() => setRecent([]));
  }, []);

  const symbols = useMemo(() => Object.keys(series || {}), [series]);
  const bt = useMemo(() => {
    if (!series) return null;
    const dates = [...new Set(Object.values(series).flatMap((rows) => rows.map((r) => r[0])))].sort().slice(-DAYS);
    const set = new Set(dates);
    const fires: { sym: string; date: string; ret: number; z: number; vol: number | null }[] = [];
    for (const [sym, rows] of Object.entries(series)) {
      if (who !== "any holding" && sym !== who) continue;
      for (const r of rows) {
        if (!set.has(r[0]) || r[3] == null) continue;
        if (Math.abs(r[3]) < z) continue;
        if (useVol && (r[4] == null || r[4] < vol)) continue;
        fires.push({ sym, date: r[0], ret: r[1], z: r[3], vol: r[4] });
      }
    }
    const byDay = new Map<string, number>();
    fires.forEach((f) => byDay.set(f.date, (byDay.get(f.date) || 0) + 1));
    const weeks = Math.max(1, dates.length / 5);
    return { dates, byDay, fires: fires.sort((a, b) => (a.date < b.date ? 1 : -1)), perWeek: fires.length / weeks };
  }, [series, who, z, vol, useVol]);

  const cycleWho = () => {
    const opts = ["any holding", ...symbols];
    setWho(opts[(opts.indexOf(who) + 1) % opts.length]);
  };

  return (
    <div>
      <h1 className="h1" style={{ margin: "6px 0 14px" }}>Alerts</h1>
      <div className="glass card">
        <p className="sentence" style={{ margin: 0 }}>
          Tell me when{" "}
          <button className="val" onClick={cycleWho} aria-label={`Which stocks: ${who}. Tap to change`}>{who}</button>{" "}
          moves more than <span className="val">{z.toFixed(1)}×</span> its normal day
          {useVol ? <> with volume above <span className="val">{vol.toFixed(1)}×</span> average</> : null}.
        </p>
        <label className="small muted" style={{ display: "block", marginTop: 14 }} htmlFor="z">Move size, in units of the stock's usual daily swing (after the market's move)</label>
        <input id="z" className="slider" type="range" min={1.5} max={5} step={0.1} value={z} onChange={(e) => setZ(+e.target.value)} />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
          <label className="small muted" htmlFor="v">Volume vs 20-day average</label>
          <button className={`chip ${useVol ? "on" : ""}`} style={{ height: 28 }} onClick={() => setUseVol((v) => !v)} aria-pressed={useVol} aria-label={`Volume condition ${useVol ? "on" : "off"}`}>{useVol ? "on" : "off"}</button>
        </div>
        <input id="v" className="slider" type="range" min={1} max={5} step={0.1} value={vol} disabled={!useVol} onChange={(e) => setVol(+e.target.value)} />
        <div className="chips" style={{ marginTop: 8 }}>
          <button className="chip" onClick={() => { setZ(3); setVol(2.5); setUseVol(true); }}>Notable move (default)</button>
          <button className="chip" onClick={() => { setZ(2.5); setUseVol(false); }}>Unusual move</button>
          <button className="chip" onClick={() => { setZ(2); setVol(1.8); setUseVol(true); }}>Move on volume</button>
        </div>
      </div>

      <div className="section-title"><h2>If this had been on</h2><span className="meta">last {DAYS} trading days</span></div>
      <div className="glass card" aria-live="polite">
        {bt ? (
          <>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <motion.span key={bt.fires.length} className="bignum" initial={{ opacity: 0.4, y: 4 }} animate={{ opacity: 1, y: 0 }}>{bt.fires.length}</motion.span>
              <span className="muted">alerts · about <b style={{ color: "var(--text)" }}>{bt.perWeek < 1 ? bt.perWeek.toFixed(1) : Math.round(bt.perWeek)}</b> a week</span>
            </div>
            <div className="strip" role="img" aria-label={`${bt.fires.length} alert days in the last ${bt.dates.length} trading days`}>
              {bt.dates.map((d) => {
                const n = bt.byDay.get(d) || 0;
                return <div key={d} className={n ? "fire" : ""} style={{ height: n ? `${Math.min(100, 40 + n * 25)}%` : undefined }} title={n ? `${d}: ${n}` : d} />;
              })}
            </div>
            <div className="strip-legend"><span>{fmtDay(bt.dates[0])}</span><span>{fmtDay(bt.dates[bt.dates.length - 1])}</span></div>
            <p className="faint small" style={{ marginBottom: 0 }}>
              {bt.perWeek > 2 ? "That's a lot of pings: most would be noise. Try a higher move size or add volume." :
                bt.perWeek < 0.3 ? "Very quiet: you'd hear about only the biggest days." : "A sensible level: roughly the days worth a look."}
            </p>
            <div style={{ marginTop: 10 }}>
              {bt.fires.slice(0, 5).map((f) => (
                <div key={f.sym + f.date} className="small" style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderTop: "1px solid var(--line)" }}>
                  <span><b>{f.sym}</b> <span className="faint">{fmtDay(f.date)}</span></span>
                  <span className="tnum"><span className={f.ret > 0 ? "up" : "down"}>{f.ret > 0 ? "+" : ""}{f.ret}%</span> · {Math.abs(f.z).toFixed(1)}×{f.vol != null ? ` · ${f.vol}× vol` : ""}</span>
                </div>
              ))}
            </div>
          </>
        ) : <div className="faint">Loading price history…</div>}
      </div>

      <div className="section-title"><h2>Recent alerts</h2><span className="meta">default rule · 14 days</span></div>
      <div className="glass row-list">
        {recent.length === 0 && <div className="row small muted">No notable moves in the last 14 days.</div>}
        {recent.map((a) => (
          <div className="row" key={a.symbol + a.date}>
            <div className="ticker-badge" aria-hidden>{a.symbol.slice(0, 4)}</div>
            <div className="grow">
              <div className="title tnum">{a.symbol} <span className={a.measures.ret_pct > 0 ? "up" : "down"}>{a.measures.ret_pct > 0 ? "+" : ""}{a.measures.ret_pct}%</span> <span className="faint small">· {fmtDay(a.date)}</span></div>
              <div className="desc">Nifty {a.measures.mkt_ret_pct > 0 ? "+" : ""}{a.measures.mkt_ret_pct}% · {Math.abs(a.measures.z).toFixed(1)}× its normal day · volume {a.measures.vol_x}× average</div>
              {a.filed_before?.map((f: Json) => (
                <div key={f.ts} style={{ marginTop: 6 }}><Cite href={f.url}>filed before: {cleanTitle(f.title)}</Cite></div>
              ))}
              {a.routine_filed_before > 0 && <div className="faint small" style={{ marginTop: 4 }}>+{a.routine_filed_before} routine filing(s) before</div>}
            </div>
            <button className="why-btn" onClick={() => onOpenResearch(a.symbol)}>Research</button>
          </div>
        ))}
      </div>
      <p className="faint small" style={{ margin: "12px 4px" }}>Filings before a move are shown for timing only. FINN does not claim they caused it.</p>
    </div>
  );
}
