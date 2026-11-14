import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { BandChart, Bars, Cite, Icon } from "../components/ui";
import { api, backendAlive, fmtCr, fmtDay, fmtNum, fmtPct, Json, nice, pageLink, signClass, snapshot } from "../lib/data";

const STAGES = ["resolving", "fetching tables", "reading transcripts", "checking promises", "judging answers",
  "reading annual report", "writing", "done"];

const VERDICT_CLASS: Record<string, string> = {
  Kept: "v-kept", Partly: "v-partly", Missed: "v-missed", "Quietly dropped": "v-dropped", "Too early": "v-early", "Not measurable": "v-nm",
};

export default function Research({ ticker, setTicker }: { ticker: string | null; setTicker: (t: string | null) => void }) {
  const [index, setIndex] = useState<Json[]>([]);
  const [symbols, setSymbols] = useState<[string, string][]>([]);
  const [q, setQ] = useState("");
  const [data, setData] = useState<Json | null>(null);
  const [job, setJob] = useState<Json | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "cold" | "offline" | "error">("idle");
  const [err, setErr] = useState("");
  const poll = useRef<number | null>(null);

  useEffect(() => {
    snapshot("research_index.json").then(setIndex).catch(() => setIndex([]));
    snapshot("symbols.json").then(setSymbols).catch(() => setSymbols([]));
    return () => { if (poll.current) window.clearInterval(poll.current); };
  }, []);

  useEffect(() => {
    setQ("");
    if (!ticker) { setData(null); setState("idle"); return; }
    let alive = true;
    setData(null); setJob(null); setErr("");
    const inSnap = index.find((r) => r.ticker === ticker);
    setState("loading");
    (async () => {
      if (inSnap) {
        try { const d = await snapshot(`research/${ticker}.json`); if (alive) { setData(d); setState("idle"); } return; } catch { /* fall through to live */ }
      }
      if (!(await backendAlive())) { if (alive) setState("offline"); return; }
      try {
        const j = await api(`/research/${encodeURIComponent(ticker)}`, { method: "POST" });
        if (!alive) return;
        setJob(j); setState("cold");
        poll.current = window.setInterval(async () => {
          try {
            const st = await api(`/research/jobs/${j.id}`);
            setJob(st);
            if (st.partial?.sections) setData({ ...st.partial, partial: true });
            if (st.status === "done") {
              window.clearInterval(poll.current!);
              setData(await api(`/research/jobs/${j.id}/result`, undefined, 20000)); setState("idle");
            } else if (st.status === "failed") {
              window.clearInterval(poll.current!); setErr(st.error || "failed"); setState("error");
            }
          } catch (e) { /* keep polling */ }
        }, 1500);
      } catch (e) { if (alive) { setErr(String(e)); setState("error"); } }
    })();
    return () => { alive = false; if (poll.current) window.clearInterval(poll.current); };
  }, [ticker, index]);

  const suggestions = useMemo(() => {
    const s = q.trim().toUpperCase();
    if (s.length < 2) return [];
    const words = s.split(/\s+/);
    return symbols.filter(([sym, name]) => sym.startsWith(s) || words.every((w) => (name || "").toUpperCase().includes(w))).slice(0, 7);
  }, [q, symbols]);

  return (
    <div>
      <h1 className="h1" style={{ margin: "6px 0 14px" }}>Research</h1>
      <div className="search">
        {Icon.search}
        <input aria-label="Search any NSE company" placeholder="Search any NSE company or ticker" value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && suggestions[0]) { setTicker(suggestions[0][0]); setQ(""); } }} />
      </div>
      <AnimatePresence>
        {suggestions.length > 0 && (
          <motion.div className="glass suggest" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {suggestions.map(([sym, name]) => (
              <button key={sym} onClick={() => { setTicker(sym); setQ(""); }}>
                <span><span className="sym">{sym}</span> <span className="muted small">{name}</span></span>
                {index.find((r) => r.ticker === sym) ? <span className="tag mint">ready</span> : <span className="tag">live</span>}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <div className="chips" style={{ marginTop: 12 }}>
        {index.map((r) => (
          <button key={r.ticker} className="chip" aria-pressed={r.ticker === ticker} onClick={() => setTicker(r.ticker)}>{r.ticker}</button>
        ))}
      </div>

      {!ticker && <Intro />}
      {state === "loading" && <div className="faint" style={{ padding: 30, textAlign: "center" }}>Opening {ticker}…</div>}
      {state === "offline" && (
        <div className="glass card" style={{ marginTop: 14 }}>
          <div className="h2">{ticker} is not in the offline snapshot</div>
          <p className="muted small">Researching a new company reads its transcripts and annual report live. Connect the FINN backend in Settings
            (it runs on the PC or a server) and FINN will build this page in a minute or two, showing the tables first.</p>
        </div>
      )}
      {state === "error" && <div className="notice" style={{ marginTop: 14 }}>Research failed: {err}</div>}
      {state === "cold" && job && <ColdStart job={job} />}
      {data && <Company d={data} />}
    </div>
  );
}

function Intro() {
  return (
    <div className="glass card" style={{ marginTop: 14 }}>
      <div className="h2">Does management keep its word?</div>
      <p className="muted small" style={{ marginBottom: 0 }}>
        FINN reads a company's last five earnings calls and its annual report, lists every target management set, and checks each one
        against the reported numbers. Every quote links to its page. Pick a company above or search any NSE name.
      </p>
    </div>
  );
}

function ColdStart({ job }: { job: Json }) {
  const i = Math.max(0, STAGES.indexOf(job.stage || "resolving"));
  return (
    <div className="glass card" style={{ marginTop: 14 }} aria-live="polite">
      <div className="card-top"><div className="h2">Reading {job.ticker} for the first time</div><span className="tag tnum">{job.progress_pct || 0}%</span></div>
      <div className="progress"><motion.div animate={{ width: `${job.progress_pct || 4}%` }} transition={{ type: "spring", stiffness: 80, damping: 20 }} /></div>
      <ul className="stages">
        {STAGES.slice(0, -1).map((s, k) => (
          <li key={s} className={k < i ? "done" : k === i ? "now" : ""}><span className="dot" />{s}</li>
        ))}
      </ul>
      <p className="faint small" style={{ marginBottom: 0 }}>Tables appear first; transcripts take a minute. Free AI tier: one company at a time.</p>
    </div>
  );
}

/* ---------------------------------------------------------------- company page */
function Company({ d }: { d: Json }) {
  const S = d.sections || {};
  const rc = S.report_card || {};
  const led = S.promise_ledger;
  const states: Json[] = d.states || [];
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 16 }}>
      <div style={{ marginBottom: 12 }}>
        <div className="h1">{d.name}</div>
        <div className="faint small">{d.ticker}{d.instrument?.bse_code ? ` · BSE ${d.instrument.bse_code}` : ""} · built {fmtDay(d.started_at)}{d.partial ? " · still reading…" : ""}</div>
      </div>
      {states.map((s) => <div key={s.state} className="notice" style={{ marginBottom: 10 }}>{s.message}</div>)}

      {(led || rc.questions_dodged) && <ReportCard rc={rc} led={led} />}
      {led && <Ledger led={led} />}
      {S.dodged_questions && <Dodged calls={S.dodged_questions} />}
      {S.narrative_vs_numbers?.length > 0 && <Story items={S.narrative_vs_numbers} />}
      {S.snapshot && <Snapshot s={S.snapshot} />}
      {S.trajectory && <Trajectory t={S.trajectory} />}
      {S.balance_sheet && <BalanceSheet b={S.balance_sheet} />}
      {S.cash_quality && <Cash c={S.cash_quality} />}
      {S.business_snapshot && <Business b={S.business_snapshot} />}
      {S.bull_bear && (S.bull_bear.bull?.length || S.bull_bear.bear?.length) ? <BullBear bb={S.bull_bear} /> : null}
      <Sources d={d} />
    </motion.div>
  );
}

function Title({ children, meta }: { children: React.ReactNode; meta?: React.ReactNode }) {
  return <div className="section-title"><h2>{children}</h2>{meta && <span className="meta">{meta}</span>}</div>;
}

function ReportCard({ rc, led }: { rc: Json; led: Json }) {
  const c = led?.counts || {};
  const scored = (c.Kept || 0) + (c.Partly || 0) + (c.Missed || 0);
  const dodged = rc.questions_dodged ? rc.questions_dodged.split(" of ") : null;
  return (
    <div className="glass scorecard hero-glow">
      <div className="small faint" style={{ textTransform: "uppercase", letterSpacing: ".09em", fontWeight: 600 }}>Management report card</div>
      <div className="grid">
        <div className="stat key"><div className="n">{scored ? `${c.Kept}/${scored}` : "–"}</div><div className="l">promises kept{scored ? "" : " (none due yet)"}</div></div>
        <div className="stat"><div className="n">{dodged ? `${dodged[0]}/${dodged[1]}` : "–"}</div><div className="l">questions dodged</div></div>
        <div className="stat"><div className="n">{(rc.topics_dropped || []).length}</div><div className="l">targets quietly dropped</div></div>
      </div>
      <div className="small muted" style={{ marginTop: 12 }}>
        {c.Missed ? `${c.Missed} missed, ` : ""}{c.Partly ? `${c.Partly} partly met, ` : ""}{c["Too early"] || 0} too early to judge, {c["Not measurable"] || 0} not measurable from the statements.
      </div>
    </div>
  );
}

function Ledger({ led }: { led: Json }) {
  const [open, setOpen] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);
  const rows: Json[] = led.promises || [];
  const shown = rows.filter((r) => showAll || r.verdict !== "Not measurable");
  const nm = rows.length - rows.filter((r) => r.verdict !== "Not measurable").length;
  return (
    <>
      <Title meta={`${led.calls?.length || 0} calls read`}>Promise ledger</Title>
      <div className="glass">
        {shown.length === 0 && <div className="row faint small" style={{ padding: 14 }}>No dated, numeric targets found in the calls read.</div>}
        {shown.map((r, i) => {
          const s = r.said;
          const unit = s.unit === "pct_growth" || s.unit === "pct_margin" ? "%" : s.unit === "rs_crore" ? " cr" : "";
          return (
            <div key={i}>
              <button className="ledger-row" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                <div className="line1">
                  <span className="what">{nice(r.metric)} {r.horizon} · {r.target}</span>
                  <span className={`verdict ${VERDICT_CLASS[r.verdict]}`}>{r.verdict}</span>
                </div>
                <div className="line2">
                  {r.scope && !/^(company|group|consolidated)$/i.test(r.scope) ? `${r.scope} · ` : ""}said {s.call_date?.slice(0, 7)} by {s.speaker}
                  {r.actual != null && <> · actual <b className="tnum" style={{ color: "var(--text)" }}>{fmtNum(r.actual, 1)}{unit}</b></>}
                </div>
              </button>
              <AnimatePresence initial={false}>
                {open === i && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden", padding: "0 14px 14px" }}>
                    {(s.low != null || s.high != null) && unit === "%" && <BandChart low={s.low} high={s.high} actual={r.actual} unit="%" />}
                    <div className="quote">
                      “{s.quote}”
                      <div className="by">{s.speaker} · call of {fmtDay(s.call_date)} <Cite href={pageLink(s.source_url, s.page)}>transcript p.{s.page}</Cite></div>
                    </div>
                    <div className="small muted" style={{ marginTop: 8 }}>{r.reason}</div>
                    {r.trail?.length > 0 && (
                      <ul className="trail">
                        {r.trail.map((e: Json, k: number) => (
                          <li key={k}><span className="ev">{e.event}</span><span>{e.call?.slice(0, 7)}{e.target ? ` · ${e.target}` : ""}{e.silent_calls ? ` · ${e.silent_calls} call(s) since` : ""}</span></li>
                        ))}
                      </ul>
                    )}
                    {r.management_explanation && (
                      <div className="quote" style={{ borderLeftColor: "var(--amber)", background: "rgba(245,200,107,0.05)" }}>
                        Management's explanation: “{r.management_explanation.quote}”
                        <div className="by">{r.management_explanation.speaker} <Cite href={pageLink(r.management_explanation.url, r.management_explanation.page)}>p.{r.management_explanation.page}</Cite></div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
        {nm > 0 && (
          <button className="collapsed-cat faint" onClick={() => setShowAll((v) => !v)}>
            <span>{showAll ? "Hide" : "Show"} statements that can't be measured from the statements</span><span className="count-pill">{nm}</span>
          </button>
        )}
      </div>
    </>
  );
}

function Dodged({ calls }: { calls: Json[] }) {
  const judged = calls.flatMap((c) => (c.judged || []).map((j: Json) => ({ ...j, call: c.call, url: c.url })));
  const shown = judged.filter((j) => j.label !== "answered");
  return (
    <>
      <Title meta={`${judged.length} questions judged`}>Did they answer?</Title>
      <div className="glass">
        {shown.length === 0 && <div className="row small muted" style={{ padding: 14 }}>Every verified question in the last {calls.length} call(s) got a direct answer.</div>}
        {shown.slice(0, 6).map((j, i) => (
          <div className="row" key={i} style={{ display: "block", padding: "12px 14px", borderTop: i ? "1px solid var(--line)" : 0 }}>
            <div className="line1" style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <b className="small">{j.analyst}</b>
              <span className={`verdict ${j.label === "dodged" ? "v-missed" : "v-partly"}`}>{j.label}</span>
            </div>
            <div className="quote" style={{ borderLeftColor: "rgba(255,255,255,0.3)", background: "rgba(255,255,255,0.03)" }}>Q: “{j.question_quote}” <Cite href={pageLink(j.url, j.question_page)}>p.{j.question_page}</Cite></div>
            <div className="quote">A: “{j.answer_quote}” <Cite href={pageLink(j.url, j.answer_page)}>p.{j.answer_page}</Cite></div>
            <div className="small faint" style={{ marginTop: 6 }}>{j.reason}</div>
          </div>
        ))}
      </div>
    </>
  );
}

function Story({ items }: { items: Json[] }) {
  return (
    <>
      <Title>Story vs numbers</Title>
      <div className="glass card">
        {items.map((x, i) => (
          <div key={i} style={{ marginTop: i ? 12 : 0 }}>
            <div className="quote">“{x.quote}”<div className="by">{x.speaker} <Cite href={pageLink(x.url, x.page)}>p.{x.page}</Cite></div></div>
            <div className="small" style={{ marginTop: 6 }}>The numbers: <b className="down">{x.numbers}</b></div>
          </div>
        ))}
      </div>
    </>
  );
}

function Snapshot({ s }: { s: Json }) {
  const l = s.latest || {};
  return (
    <>
      <Title meta={`latest quarter ${s.latest_quarter}`}>Snapshot</Title>
      <div className="glass card kv">
        <span className="k">Market cap</span><span className="v">{fmtCr(s.market_cap_cr)}</span>
        <span className="k">P/E</span><span className="v">{s.pe ?? "–"}</span>
        {l.revenue != null && <><span className="k">Quarter revenue</span><span className="v">{fmtCr(l.revenue)}</span></>}
        {l.pat != null && <><span className="k">Quarter profit</span><span className="v">{fmtCr(l.pat)}</span></>}
        {l.gross_npa_pct != null && <><span className="k">Gross / net NPA</span><span className="v">{l.gross_npa_pct}% / {l.net_npa_pct}%</span></>}
        {s.roe_pct != null && <><span className="k">ROE</span><span className="v">{s.roe_pct}%</span></>}
        {s.roce_pct != null && !s.lender && <><span className="k">ROCE</span><span className="v">{s.roce_pct}%</span></>}
      </div>
    </>
  );
}

function Trajectory({ t }: { t: Json }) {
  const rows: Json[] = (t.annual || []).slice(-7);
  const c3 = t.cagr_pct?.["3y"] || {}, c5 = t.cagr_pct?.["5y"] || {};
  return (
    <>
      <Title meta="revenue bars · margin line">Trajectory</Title>
      <div className="glass card">
        <Bars label="Annual revenue with operating margin" data={rows.map((r) => ({ x: `FY${r.year_end.slice(2, 4)}`, y: r.revenue, line: r.ebitda_margin_pct }))} />
        <div className="kv" style={{ marginTop: 8 }}>
          <span className="k">Revenue CAGR 3y / 5y</span><span className="v">{fmtPct(c3.revenue)} / {fmtPct(c5.revenue)}</span>
          <span className="k">Profit CAGR 3y / 5y</span><span className="v">{fmtPct(c3.pat)} / {fmtPct(c5.pat)}</span>
          <span className="k">Quarters with YoY revenue growth</span><span className="v">{t.quarters_with_yoy_revenue_growth}</span>
        </div>
      </div>
    </>
  );
}

function BalanceSheet({ b }: { b: Json }) {
  if (b.available === false) return null;
  const wc = b.working_capital || {};
  return (
    <>
      <Title meta={`as of ${b.as_of}`}>Balance sheet</Title>
      <div className="glass card kv">
        <span className="k">Net worth</span><span className="v">{fmtCr(b.net_worth)}</span>
        <span className="k">Borrowings</span><span className="v">{fmtCr(b.borrowings)}</span>
        {b.lender ? (
          <>
            <span className="k">Deposits</span><span className="v">{fmtCr(b.deposits)}</span>
            <span className="k">Deposit growth</span><span className={`v ${signClass(b.deposit_growth_pct)}`}>{fmtPct(b.deposit_growth_pct)}</span>
            <span className="k">Equity / assets</span><span className="v">{b.equity_to_assets_pct}%</span>
          </>
        ) : (
          <>
            <span className="k">Debt / equity</span><span className="v">{b.debt_to_equity ?? "–"}</span>
            {wc.ccc_days != null && <><span className="k">Cash conversion cycle</span><span className="v">{fmtNum(wc.ccc_days)} days</span></>}
            {wc.debtor_days != null && <><span className="k">Debtor days</span><span className="v">{fmtNum(wc.debtor_days)}</span></>}
          </>
        )}
      </div>
      {b.note && <p className="faint small" style={{ margin: "6px 4px" }}>{b.note}</p>}
    </>
  );
}

function Cash({ c }: { c: Json }) {
  if (c.available === false) return null;
  const rows: Json[] = (c.years || []).slice(-6);
  return (
    <>
      <Title meta="operating cash vs profit">Cash quality</Title>
      <div className="glass card">
        {!c.lender && (
          <svg viewBox="0 0 340 110" width="100%" role="img" aria-label="Operating cash flow compared with profit by year">
            {rows.map((r, i) => {
              const max = Math.max(...rows.flatMap((x) => [x.cfo || 0, x.pat || 0]), 1);
              const bw = 300 / rows.length, x0 = 20 + i * bw;
              const h1 = ((r.pat || 0) / max) * 80, h2 = ((r.cfo || 0) / max) * 80;
              return (
                <g key={r.year_end}>
                  <rect x={x0 + bw * 0.15} y={90 - h1} width={bw * 0.32} height={Math.max(h1, 1)} rx="3" fill="rgba(255,255,255,0.25)" />
                  <rect x={x0 + bw * 0.5} y={90 - h2} width={bw * 0.32} height={Math.max(h2, 1)} rx="3" fill="var(--mint)" />
                  <text x={x0 + bw / 2} y="104" textAnchor="middle" fontSize="10" fill="rgba(234,245,238,0.42)">FY{r.year_end.slice(2, 4)}</text>
                </g>
              );
            })}
          </svg>
        )}
        <div className="small muted">{c.reading || c.note}</div>
        {!c.lender && <div className="faint small" style={{ marginTop: 4 }}>grey = profit · mint = operating cash flow</div>}
      </div>
    </>
  );
}

function Business({ b }: { b: Json }) {
  const segs: Json[] = b.segments || [];
  return (
    <>
      <Title meta={b.status === "verified" ? "checked vs revenue" : b.status === "unverified" ? "not verified" : ""}>What it sells</Title>
      <div className="glass card">
        {segs.length === 0 && <div className="small muted">{b.note || "No segment table found in the annual report."}</div>}
        {segs.slice(0, 6).map((s) => (
          <div key={s.name} style={{ marginBottom: 9 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13.5 }}>
              <span>{s.name}</span><span className="tnum muted">{s.mix_pct}%{s.growth_pct != null && <span className={signClass(s.growth_pct)}> · {fmtPct(s.growth_pct)}</span>}</span>
            </div>
            <div className="progress" style={{ marginTop: 4 }}><div style={{ width: `${s.mix_pct}%` }} /></div>
          </div>
        ))}
        {b.check && <div className="faint small">{b.status === "verified" ? "✓ " : ""}{b.check}</div>}
        {b.source?.url && <div style={{ marginTop: 8 }}><Cite href={pageLink(b.source.url, b.pages?.[0])}>{b.source.title}{b.pages ? ` p.${b.pages.join(", ")}` : ""}</Cite></div>}
      </div>
    </>
  );
}

function BullBear({ bb }: { bb: Json }) {
  return (
    <>
      <Title meta="every point cites a number">Bull vs bear</Title>
      <div className="glass card">
        <div className="small" style={{ fontWeight: 700, color: "var(--up)", letterSpacing: ".06em" }}>BULL</div>
        <ul className="bullets">{bb.bull.map((x: Json, i: number) => <li key={i}><span className="up">▲</span><span>{x.text} <span className="faint small">({x.cites.map((c: Json) => c.source).join(", ")})</span></span></li>)}</ul>
        <div className="small" style={{ fontWeight: 700, color: "var(--down)", letterSpacing: ".06em", marginTop: 12 }}>BEAR</div>
        <ul className="bullets">{bb.bear.map((x: Json, i: number) => <li key={i}><span className="down">▼</span><span>{x.text} <span className="faint small">({x.cites.map((c: Json) => c.source).join(", ")})</span></span></li>)}</ul>
        {bb.removed?.length > 0 && <div className="faint small" style={{ marginTop: 8 }}>{bb.removed.length} point(s) removed for not standing on a number.</div>}
      </div>
    </>
  );
}

function Sources({ d }: { d: Json }) {
  const ts: Json[] = d.transcripts || [];
  const ar = d.sections?.business_snapshot?.source;
  return (
    <>
      <Title>Sources</Title>
      <div className="glass card" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {ts.map((t) => <Cite key={t.url} href={t.url}>call {t.call.slice(0, 7)}</Cite>)}
        {ar?.url && <Cite href={ar.url}>{ar.title}</Cite>}
        {d.sections?.snapshot?.source && <Cite href={d.sections.snapshot.source}>statement tables (screener.in)</Cite>}
        <div className="faint small" style={{ width: "100%" }}>Numbers from the statement tables; quotes checked word for word on the page cited. Built {fmtDay(d.started_at)}.</div>
      </div>
    </>
  );
}
