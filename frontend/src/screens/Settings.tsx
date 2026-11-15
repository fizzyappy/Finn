import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { catLabel, fmtNum, fmtWhen, Json, nice, prefs, snapshot, wakeBackend } from "../lib/data";

const SOURCE_LABEL: Record<string, string> = {
  bse_api: "BSE announcements API", nse_api: "NSE announcements API",
  screener_recent: "Screener recent list", rss_store: "BSE + NSE official RSS",
};

const TYPES = ["results", "M&A", "management_change", "fund_raise", "litigation", "insider_trading", "pledging",
  "credit_rating", "capex", "dividend", "bonus_split", "press_release"];

export default function Settings() {
  const [meta, setMeta] = useState<Json | null>(null);
  const [base, setBase] = useState(prefs.apiBase());
  const [status, setStatus] = useState<string>("");
  const [tune, setTune] = useState(prefs.tune());

  useEffect(() => { snapshot("meta.json").then(setMeta).catch(() => setMeta(null)); }, []);

  const test = async () => {
    prefs.setApiBase(base);
    setStatus("checking…");
    const ok = await wakeBackend(() => setStatus("waking up the free server (up to a minute)…"));
    setStatus(ok ? "connected: live research for any company is on" : "not reachable right now: using the offline snapshot");
  };

  const usage = meta?.llm_all_time?.models || {};
  const calls = Object.values(usage).reduce((a: number, m: Json) => a + m.api_calls, 0) as number;
  const tokens = Object.values(usage).reduce((a: number, m: Json) => a + m.tokens_in + m.tokens_out, 0) as number;
  const hits = Object.values(usage).reduce((a: number, m: Json) => a + (m.cache_hits || 0), 0) as number;
  const hitPct = calls + hits ? Math.round((hits / (calls + hits)) * 100) : 0;
  const holdings: Json[] = meta?.portfolio?.holdings || [];
  const src = meta?.filings_sources || {};
  const srcCount: Record<string, { ok: number; blocked: number }> = {};
  Object.values(src).forEach((st: Json) => Object.entries(st || {}).forEach(([k, v]) => {
    srcCount[k] ||= { ok: 0, blocked: 0 };
    if (String(v).startsWith("ok")) srcCount[k].ok += 1; else srcCount[k].blocked += 1;
  }));

  return (
    <div>
      <h1 className="h1" style={{ margin: "6px 0 2px" }}>Settings</h1>
      <p className="small muted" style={{ margin: "0 0 12px" }}>Your portfolio, which announcements reach you, and what FINN costs to run.</p>

      <div className="section-title"><h2>Your portfolio</h2><span className="meta">{holdings.length} holdings</span></div>
      <div className="glass card weights">
        {holdings.map((h) => (
          <div className="w-row" key={h.symbol}>
            <a className="sym-link" href={`#research/${h.symbol}`}>{h.symbol}</a>
            <div className="bar"><div style={{ width: `${(h.weight / 0.1) * 100}%` }} /></div>
            <span className="tnum muted" style={{ textAlign: "right" }}>{(h.weight * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>

      <div className="section-title"><h2>Announcement types</h2><span className="meta">tap to change</span></div>
      <div className="glass card">
        {TYPES.map((cat) => {
          const v = tune[cat] ?? 1;
          const level = v <= 0.35 ? "mute" : v >= 1.4 ? "boost" : v === 1 ? "normal" : "tuned";
          const set = (x: number) => { const t = { ...tune, [cat]: x }; if (x === 1) delete t[cat]; prefs.setTune(t); setTune(t); };
          return (
            <div key={cat} className="type-row">
              <span className="small">{catLabel(cat)}{level === "tuned" ? <span className="faint"> · ×{v.toFixed(2)} from swipes</span> : null}</span>
              <span className="seg" role="group" aria-label={`${catLabel(cat)} alerts`}>
                {([["mute", "Mute", 0.3], ["normal", "Normal", 1], ["boost", "Boost", 1.5]] as const).map(([k, label, x]) => (
                  <button key={k} className={`seg-${k}`} aria-pressed={level === k} onClick={() => set(x)}>
                    {level === k && <motion.span layoutId={`seg-${cat}`} className="seg-thumb" transition={{ type: "spring", stiffness: 320, damping: 28, mass: 0.8 }} />}
                    <span className="seg-label">{label}</span>
                  </button>
                ))}
              </span>
            </div>
          );
        })}
        <p className="faint small" style={{ marginBottom: 0 }}>Boost moves a type up to "needs your attention"; mute collapses it with the routine filings. Swiping a card left also turns its type down.</p>
      </div>

      <div className="section-title"><h2>Data</h2><span className="meta">as of {fmtWhen(meta?.generated_at)}</span></div>
      <div className="glass card kv">
        <span className="k">Prices (Yahoo, end of day)</span><span className="v">{meta?.prices?.nifty?.last_date || "–"}</span>
        {Object.entries(srcCount).filter(([, c]) => c.ok).map(([k, c]) => (
          <span key={k} style={{ display: "contents" }}>
            <span className="k">Filings: {SOURCE_LABEL[k] || nice(k)}</span>
            <span className="v">{c.ok}/{holdings.length} holdings</span>
          </span>
        ))}
      </div>


      <div className="section-title"><h2>How FINN thinks</h2></div>
      <div className="glass card">
        <ol className="steps">
          <li><b>Filter.</b> Every filing from your holdings is sorted into 17 types by rules; Gemini reads page 1 only when the rules are unsure.</li>
          <li><b>Rank.</b> A score from the type, the details (a CEO quitting, a deal's size vs market cap), your holding's weight, your swipes, and how the stock moved.</li>
          <li><b>Verify.</b> Numbers are read from the filing and checked by Python (totals, PBT − tax = PAT, a second source). Quotes must appear word for word on the page cited.</li>
          <li><b>Hold management to account.</b> Every target from the last five calls is measured against the reported numbers. Python decides the verdict, not the model.</li>
        </ol>
        <p className="faint small" style={{ marginBottom: 0 }}>Primary sources only: exchange filings, transcripts and annual reports. FINN does not give investment advice.</p>
      </div>

      <div className="section-title"><h2>What it costs to run</h2><span className="meta">AI usage</span></div>
      <div className="glass card">
        <div className="cost-line tnum">
          <span><b>$0</b> spent</span><span><b>{fmtNum(calls)}</b> AI calls</span>
          <span><b>{hitPct}%</b> from cache</span><span><b>{tokens > 1e6 ? `${(tokens / 1e6).toFixed(1)}M` : `${Math.round(tokens / 1000)}k`}</b> tokens</span>
        </div>
        <p className="faint small" style={{ marginBottom: 0 }}>Rules do most of the work; Gemini (free tier) is used only where rules can't, and every answer is cached by its exact input, so a filing is read once for everyone.</p>
      </div>

      <details className="glass card dev" style={{ marginTop: 26 }}>
        <summary className="small muted">Developer: research engine address</summary>
        <label className="small muted" htmlFor="api" style={{ display: "block", marginTop: 10 }}>Used for companies outside the built-in data</label>
        <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
          <input id="api" className="field" placeholder="https://finn-api.example.com" value={base} onChange={(e) => setBase(e.target.value)} />
          <button className="btn small" onClick={test}>Connect</button>
        </div>
        {status && <div className="small muted" style={{ marginTop: 8 }} role="status">{status}</div>}
      </details>
    </div>
  );
}
