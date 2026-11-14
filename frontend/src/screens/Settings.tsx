import { useEffect, useState } from "react";
import { backendAlive, fmtNum, fmtWhen, Json, nice, prefs, snapshot } from "../lib/data";

const SOURCE_LABEL: Record<string, string> = {
  bse_api: "BSE announcements API", nse_api: "NSE announcements API",
  screener_recent: "Screener recent list", rss_store: "BSE + NSE official RSS",
};

export default function Settings() {
  const [meta, setMeta] = useState<Json | null>(null);
  const [base, setBase] = useState(prefs.apiBase());
  const [status, setStatus] = useState<string>("");
  const [tune, setTune] = useState(prefs.tune());

  useEffect(() => { snapshot("meta.json").then(setMeta).catch(() => setMeta(null)); }, []);

  const test = async () => {
    prefs.setApiBase(base);
    setStatus("checking…");
    setStatus((await backendAlive()) ? "connected: live research for any company is on" : "not reachable: using the offline snapshot");
  };

  const usage = meta?.llm_all_time?.models || {};
  const calls = Object.values(usage).reduce((a: number, m: Json) => a + m.api_calls, 0) as number;
  const tokens = Object.values(usage).reduce((a: number, m: Json) => a + m.tokens_in + m.tokens_out, 0) as number;
  const today = meta?.llm_today?.models || {};
  const todayCalls = Object.values(today).reduce((a: number, m: Json) => a + m.api_calls, 0) as number;
  const todayHits = Object.values(today).reduce((a: number, m: Json) => a + m.cache_hits, 0) as number;
  const hitPct = todayCalls + todayHits ? Math.round((todayHits / (todayCalls + todayHits)) * 100) : 0;
  const holdings: Json[] = meta?.portfolio?.holdings || [];
  const src = meta?.filings_sources || {};
  const srcCount: Record<string, { ok: number; blocked: number }> = {};
  Object.values(src).forEach((st: Json) => Object.entries(st || {}).forEach(([k, v]) => {
    srcCount[k] ||= { ok: 0, blocked: 0 };
    if (String(v).startsWith("ok")) srcCount[k].ok += 1; else srcCount[k].blocked += 1;
  }));

  return (
    <div>
      <h1 className="h1" style={{ margin: "6px 0 14px" }}>Settings</h1>

      <div className="glass scorecard hero-glow">
        <div className="small faint" style={{ textTransform: "uppercase", letterSpacing: ".09em", fontWeight: 600 }}>Cost meter</div>
        <div style={{ marginTop: 8 }}><span className="bignum">$0.00</span> <span className="muted">spent today · {hitPct}% answered from cache</span></div>
        <div className="grid">
          <div className="stat"><div className="n">{fmtNum(todayCalls)}</div><div className="l">AI calls today</div></div>
          <div className="stat"><div className="n">{fmtNum(calls)}</div><div className="l">AI calls ever</div></div>
          <div className="stat"><div className="n">{tokens > 1e6 ? `${(tokens / 1e6).toFixed(1)}M` : `${Math.round(tokens / 1000)}k`}</div><div className="l">tokens ever</div></div>
        </div>
        <p className="faint small" style={{ marginBottom: 0 }}>Gemini free tier. Every answer is cached by its exact input, so a filing is read once for everyone.</p>
      </div>

      <div className="section-title"><h2>Your portfolio</h2><span className="meta">{holdings.length} holdings</span></div>
      <div className="glass card weights">
        {holdings.map((h) => (
          <div className="w-row" key={h.symbol}>
            <b>{h.symbol}</b>
            <div className="bar"><div style={{ width: `${(h.weight / 0.1) * 100}%` }} /></div>
            <span className="tnum muted" style={{ textAlign: "right" }}>{(h.weight * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>

      {Object.keys(tune).length > 0 && (
        <>
          <div className="section-title"><h2>Tuned by your swipes</h2></div>
          <div className="glass card">
            {Object.entries(tune).map(([cat, v]) => <div key={cat} className="kv"><span className="k">{nice(cat)}</span><span className="v">×{v.toFixed(2)}</span></div>)}
            <button className="btn secondary small" style={{ marginTop: 12 }} onClick={() => { prefs.setTune({}); setTune({}); }}>Reset</button>
          </div>
        </>
      )}

      <div className="section-title"><h2>Data</h2><span className="meta">as of {fmtWhen(meta?.generated_at)}</span></div>
      <div className="glass card kv">
        <span className="k">Prices (Yahoo, end of day)</span><span className="v">{meta?.prices?.nifty?.last_date || "–"}</span>
        {Object.entries(srcCount).map(([k, c]) => (
          <span key={k} style={{ display: "contents" }}>
            <span className="k">Filings: {SOURCE_LABEL[k] || nice(k)}</span>
            <span className={`v ${c.ok ? "" : "faint"}`}>{c.ok ? `ok (${c.ok})` : "refused"}</span>
          </span>
        ))}
      </div>
      {meta?.filings_note && <p className="faint small" style={{ margin: "8px 4px" }}>{meta.filings_note}</p>}

      <div className="section-title"><h2>Live backend</h2></div>
      <div className="glass card">
        <label className="small muted" htmlFor="api">FINN backend URL (for companies not in the snapshot)</label>
        <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
          <input id="api" className="field" placeholder="https://finn-api.example.com" value={base} onChange={(e) => setBase(e.target.value)} />
          <button className="btn small" onClick={test}>Connect</button>
        </div>
        {status && <div className="small muted" style={{ marginTop: 8 }} role="status">{status}</div>}
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
    </div>
  );
}
