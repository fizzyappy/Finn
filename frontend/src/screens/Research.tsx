import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { BandChart, Bars, Cite, Icon } from "../components/ui";
import { api, callQuarter, fmtCr, fmtDay, fmtNum, fmtPct, Json, metricLabel, pageLink, prefs, rupee, signClass, snapshot, wakeBackend } from "../lib/data";

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
  const [state, setState] = useState<"idle" | "loading" | "waking" | "asleep" | "cold" | "offline" | "error">("idle");
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
      if (!prefs.apiBase()) { if (alive) setState("offline"); return; }
      const up = await wakeBackend(() => { if (alive) setState("waking"); });
      if (!up) { if (alive) setState("asleep"); return; }
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
      } catch (e) {
        if (alive) {
          setErr(/429/.test(String(e)) ? "Too many new companies from this device in the last hour (the free AI tier is shared). Try again later, or pick one of the companies below." : String(e));
          setState("error");
        }
      }
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
      <h1 className="h1" style={{ margin: "6px 0 2px" }}>Research</h1>
      <p className="small muted" style={{ margin: "0 0 12px" }}>Pick a company: what management promised, what it delivered, and the numbers behind it.</p>
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

      {!ticker && <Intro index={index} onPick={setTicker} />}
      {state === "loading" && <div className="faint" style={{ padding: 30, textAlign: "center" }}>Opening {ticker}…</div>}
      {state === "offline" && (
        <div className="glass card" style={{ marginTop: 14 }}>
          <div className="h2">{ticker} is not in the offline snapshot</div>
          <p className="muted small">Researching a new company reads its transcripts and annual report live. Connect the FINN backend in Settings
            (it runs on the PC or a server) and FINN will build this page in a minute or two, showing the tables first.</p>
        </div>
      )}
      {state === "waking" && (
        <div className="glass card" style={{ marginTop: 14 }} aria-live="polite">
          <div className="card-top"><div className="h2">Waking up the research engine</div><span className="tag">up to 50 s</span></div>
          <div className="progress"><motion.div initial={{ width: "4%" }} animate={{ width: "92%" }} transition={{ duration: 50, ease: "linear" }} /></div>
          <p className="muted small" style={{ marginBottom: 0 }}>
            The free server that reads new companies sleeps when nobody is using it. It is starting now; {ticker} will begin right after.
          </p>
        </div>
      )}
      {state === "asleep" && (
        <div className="notice" style={{ marginTop: 14 }}>
          The research engine did not answer within a minute. The {index.length} companies above still work from the built-in data; try {ticker} again in a moment.
        </div>
      )}
      {state === "error" && (
        <div className="notice" style={{ marginTop: 14 }}>
          {/unknown company|404/i.test(err) ? `FINN could not find "${ticker}" on NSE. Try the search box above.` :
            /refused|503/i.test(err) ? "A data source refused the research server just now. The built-in companies still work; try again later." :
            `Research failed: ${err}`}
        </div>
      )}
      {state === "cold" && job && <ColdStart job={job} />}
      {data && <Company d={data} onBack={() => setTicker("")} />}
    </div>
  );
}

function Intro({ index, onPick }: { index: Json[]; onPick: (t: string) => void }) {
  const ratio = (s?: string) => {
    const m = /^(\d+) of (\d+)$/.exec(s || "");
    return m ? { a: +m[1], b: +m[2] } : null;
  };
  const weight = (r: Json) => {
    const k = ratio(r.kept), d = ratio(r.dodged);
    return (k && k.b ? 2 : 0) + (d && d.a ? 1 : 0);
  };
  const rows = [...index].sort((x, y) => weight(y) - weight(x) || Number(y.in_portfolio) - Number(x.in_portfolio) || x.ticker.localeCompare(y.ticker));
  const shortName = (n?: string) => (n || "").replace(/ \(India\)/, "").replace(/ (Ltd|Limited)\.?$/, "");
  return (
    <>
      <p className="small muted" style={{ margin: "14px 2px 0" }}>Each scorecard checks management's targets from the last five calls against the reported numbers.</p>
      {([["Your holdings", rows.filter((r) => r.in_portfolio)], ["Other companies", rows.filter((r) => !r.in_portfolio)]] as [string, Json[]][])
        .filter(([, list]) => list.length > 0).map(([title, list]) => (
        <div key={title}>
          <div className="section-title"><h2>{title}</h2><span className="meta">{list.length}</span></div>
          <div className="glass">
            {list.map((r) => {
              const k = ratio(r.kept), d = ratio(r.dodged);
              return (
                <button key={r.ticker} className="ledger-row score-row" onClick={() => onPick(r.ticker)}>
                  <div className="score-left">
                    <div className="what">{r.ticker}</div>
                    <div className="score-name">{shortName(r.name)}</div>
                    <div className="line2">{r.next_due ? `next due ${r.next_due.replace(/^by /, "")}` : "no target due"}{r.last_call ? ` · last call ${callQuarter(r.last_call)}` : ""}</div>
                  </div>
                  <div className="score-pills tnum">
                    {k && k.b
                      ? <span className={`verdict ${k.a / k.b >= 0.6 ? "v-kept" : k.a / k.b >= 0.34 ? "v-partly" : "v-missed"}`}>{k.a}/{k.b} kept</span>
                      : r.tracked ? <span className="verdict v-nm">{r.tracked} tracked</span> : null}
                    {d && d.a > 0 && <span className="verdict v-missed">{d.a} dodged</span>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </>
  );
}

function ColdStart({ job }: { job: Json }) {
  const i = Math.max(0, STAGES.indexOf(job.stage || "resolving"));
  return (
    <div className="glass card" style={{ marginTop: 14 }} aria-live="polite">
      <div className="card-top"><div className="h2">Reading {job.ticker} for the first time</div>
        <span className="tag tnum">{job.status === "queued" && job.ahead ? `${job.ahead} ahead` : `${job.progress_pct || 0}%`}</span></div>
      <div className="progress"><motion.div animate={{ width: `${job.progress_pct || 4}%` }} transition={{ type: "spring", stiffness: 80, damping: 20 }} /></div>
      <ul className="stages">
        {STAGES.slice(0, -1).map((s, k) => (
          <li key={s} className={k < i ? "done" : k === i ? "now" : ""}><span className="dot" />{s}</li>
        ))}
      </ul>
      <p className="faint small" style={{ marginBottom: 0 }}>
        {job.status === "queued" ? (job.ahead ? `${job.ahead} ahead of you · about ${job.wait_minutes || job.ahead * 4} min. ` : "Starting… ") : ""}
        Tables appear first; transcripts take a few minutes. Free AI tier: one company at a time.
      </p>
    </div>
  );
}

/* ---------------------------------------------------------------- company page */
const JUMPS: [string, string][] = [["ask", "Ask"], ["promise-ledger", "Promises"], ["did-they-answer", "Answers"],
  ["snapshot", "Numbers"], ["bull-vs-bear", "Bull/bear"], ["sources", "Sources"]];
const slug = (x: React.ReactNode) => (typeof x === "string" ? x : "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function JumpBar() {
  const [have, setHave] = useState<[string, string][]>([]);
  useEffect(() => { setHave(JUMPS.filter(([id]) => document.getElementById(id))); }, []);
  if (have.length < 3) return null;
  return (
    <div className="jumpbar" role="navigation" aria-label="Jump to section">
      {have.map(([id, label]) => (
        <button key={id} className="chip" onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })}>{label}</button>
      ))}
    </div>
  );
}

function Take({ t }: { t: Json }) {
  return (
    <motion.div className="glass card take" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginBottom: 12 }}>
      <div className="take-label">FINN's take</div>
      <div className="take-line">
        {t.parts.map((x: Json, i: number) => (
          <span key={i}>{i > 0 && <span className="take-dot"> · </span>}<span className={`take-${x.tone}`}>{x.text}</span></span>
        ))}
      </div>
      <div className="faint small" style={{ marginTop: 6 }}>Growth: 3-year average → latest quarter vs a year ago. Written by Python from the facts below.</div>
    </motion.div>
  );
}

function Company({ d, onBack }: { d: Json; onBack: () => void }) {
  const S = d.sections || {};
  const rc = S.report_card || {};
  const led = S.promise_ledger;
  const states: Json[] = d.states || [];
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 16 }}>
      <button className="back-link" onClick={onBack}>← All companies</button>
      <div style={{ marginBottom: 12 }}>
        <div className="h1">{d.name}</div>
        <div className="faint small">{d.ticker}{S.snapshot?.price ? ` · ₹${fmtNum(S.snapshot.price, S.snapshot.price < 100 ? 1 : 0)}` : ""}{S.snapshot?.market_cap_cr ? ` · m-cap ${fmtCr(S.snapshot.market_cap_cr)}` : ""} · updated {fmtDay(d.started_at)}{d.partial ? " · still reading…" : ""}</div>
      </div>
      {S.take?.parts?.length > 0 && <Take t={S.take} />}
      {states.map((s) => <div key={s.state} className="notice" style={{ marginBottom: 10 }}>{s.message}</div>)}

      {(led || rc.questions_dodged) && <ReportCard rc={rc} led={led} />}
      {!d.partial && <JumpBar />}
      {!d.partial && <AskBox ticker={d.ticker} name={d.name} d={d} />}
      {led && <Ledger led={led} />}
      {S.dodged_questions && <Dodged calls={S.dodged_questions} />}
      {S.narrative_vs_numbers?.length > 0 && <Story items={S.narrative_vs_numbers} />}
      {S.snapshot && <Snapshot s={S.snapshot} />}
      {S.bank && <Bank b={S.bank} yearGrowth={S.balance_sheet?.deposit_growth_pct} />}
      {S.trajectory && <Trajectory t={S.trajectory} lender={!!S.snapshot?.lender} />}
      {S.balance_sheet && <BalanceSheet b={S.balance_sheet} />}
      {S.cash_quality && <Cash c={S.cash_quality} />}
      {S.business_snapshot && <Business b={S.business_snapshot} />}
      {S.bull_bear && (S.bull_bear.bull?.length || S.bull_bear.bear?.length) ? <BullBear bb={S.bull_bear} /> : null}
      <Sources d={d} />
    </motion.div>
  );
}

function suggestFor(d: Json): string[] {
  const S = d?.sections || {};
  const c = S.promise_ledger?.counts || {};
  const out: string[] = [];
  if ((c.Kept || 0) + (c.Missed || 0) + (c.Partly || 0) > 0) out.push("Did they meet last year's guidance?");
  if (c["Too early"]) out.push("What targets have they set for this year?");
  if (S.snapshot?.lender) out.push("How fast are deposits and loans growing?");
  else out.push("How much debt do they have?");
  if ((S.business_snapshot?.segments || []).length) out.push("Which segment is the biggest?");
  out.push("How did profit change last quarter?");
  return out.slice(0, 3);
}

function AskBox({ ticker, name, d }: { ticker: string; name: string; d?: Json }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [a, setA] = useState<Json | null>(null);
  const short = (name || ticker).replace(/ (Ltd|Limited)\.?$/, "");
  const ask = async (question: string) => {
    if (question.trim().length < 4) return;
    setA(null);
    if (!prefs.apiBase()) { setA({ status: "offline", answer: "Asking needs the research engine. Connect it in Settings." }); return; }
    setBusy("Thinking…");
    const up = await wakeBackend(() => setBusy("Waking up the research engine (up to 50 s)…"));
    if (!up) { setBusy(null); setA({ status: "offline", answer: "The research engine did not answer. Try again in a minute." }); return; }
    setBusy("Reading this company's sources…");
    try {
      setA(await api(`/ask/${encodeURIComponent(ticker)}`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }) }, 90000));
    } catch (e) {
      setA({ status: "error", answer: /404/.test(String(e)) ? `The research engine has not read ${ticker} yet.`
        : /429/.test(String(e)) ? "That's a lot of questions from this device in an hour (the free AI tier is shared). Try again in a few minutes."
        : "Something went wrong. Try again." });
    } finally { setBusy(null); }
  };
  const examples = suggestFor(d);
  return (
    <>
      <Title meta="sourced answers" id="ask">Ask about {short}</Title>
      <div className="glass card">
        <form onSubmit={(e) => { e.preventDefault(); ask(q); }} style={{ display: "flex", gap: 8 }}>
          <input className="field" aria-label={`Ask a question about ${short}`} placeholder="e.g. Did they meet their margin target?"
            value={q} onChange={(e) => setQ(e.target.value)} maxLength={300} />
          <button className="btn small" type="submit" disabled={!!busy || q.trim().length < 4}>Ask</button>
        </form>
        <div className="chips" style={{ marginTop: 8 }}>
          {examples.map((x) => <button key={x} className="chip" style={{ height: 30, fontSize: 12.5 }} onClick={() => { setQ(x); ask(x); }}>{x}</button>)}
        </div>
        {busy && <div className="small muted" style={{ marginTop: 10 }} aria-live="polite">{busy}</div>}
        {a && (
          <motion.div data-testid="ask-answer" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 12 }} aria-live="polite">
            <div className={a.status === "answered" ? "quote" : "notice"}>{a.answer}</div>
            {a.citations?.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                {a.citations.map((c: Json) => <Cite key={c.id} href={pageLink(c.url, c.page)}>{c.source}{c.page ? ` p.${c.page}` : ""}</Cite>)}
              </div>
            )}
            {a.status === "answered" && <div className="faint small" style={{ marginTop: 6 }}>Every number above was checked against the cited sources.</div>}
          </motion.div>
        )}
      </div>
    </>
  );
}

function Title({ children, meta, id }: { children: React.ReactNode; meta?: React.ReactNode; id?: string }) {
  return (
    <motion.div className="section-title" id={id || slug(children) || undefined}
      initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}>
      <h2>{children}</h2>{meta && <span className="meta">{meta}</span>}
    </motion.div>
  );
}

function ReportCard({ rc, led }: { rc: Json; led: Json }) {
  const c = led?.counts || {};
  const scored = (c.Kept || 0) + (c.Partly || 0) + (c.Missed || 0);
  const dodged = rc.questions_dodged ? rc.questions_dodged.split(" of ") : null;
  const dropped = (rc.topics_dropped || []).length;
  if (!scored && !dropped && !(dodged && +dodged[0] > 0)) {
    return (
      <div className="glass card small muted">
        <b style={{ color: "var(--text)" }}>Management report card:</b> {led?.promises?.length || 0} targets tracked
        {c["Too early"] ? `, ${c["Too early"]} due later` : ""}; none due yet.{dodged ? ` Answered ${dodged[1]} of ${dodged[1]} analyst questions.` : ""}
      </div>
    );
  }
  return (
    <div className="glass scorecard hero-glow">
      <div className="small faint" style={{ textTransform: "uppercase", letterSpacing: ".09em", fontWeight: 600 }}>Management report card</div>
      <div className="grid">
        <div className={`stat ${scored ? "key" : "zero"}`}><div className="n">{scored ? `${c.Kept}/${scored}` : "–"}</div><div className="l">{scored ? "promises kept" : "no promises due yet"}</div></div>
        <div className={`stat ${dodged ? "" : "zero"}`}>
          <div className="n">{dodged ? `${+dodged[1] - +dodged[0]}/${dodged[1]}` : "–"}</div>
          <div className="l">{dodged ? `questions answered${+dodged[0] ? ` · ${dodged[0]} dodged` : ""}` : "no calls checked"}</div>
        </div>
        <div className={`stat ${dropped ? "" : "zero"}`}><div className="n">{dropped}</div><div className="l">{dropped === 1 ? "target quietly dropped" : "targets quietly dropped"}</div></div>
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
                  <span className="what">{metricLabel(r.metric)} {r.horizon} · {r.target}</span>
                  <span className={`verdict ${VERDICT_CLASS[r.verdict]}`}>{r.verdict}</span>
                </div>
                <div className="line2">
                  {r.scope && !/^(company|group|consolidated)$/i.test(r.scope) ? `${r.scope} · ` : ""}said on the {callQuarter(s.call_date)} call by {s.speaker}
                  {r.actual != null && <> · actual <b className="tnum" style={{ color: "var(--text)" }}>{fmtNum(r.actual, 1)}{unit}</b></>}
                </div>
              </button>
              <AnimatePresence initial={false}>
                {open === i && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: "hidden", padding: "0 14px 14px" }}>
                    {(s.low != null || s.high != null) && unit === "%" && <BandChart low={s.low} high={s.high} actual={r.actual} unit="%" />}
                    <div className="quote">
                      “{s.quote}”
                      <div className="by">{s.speaker} · {callQuarter(s.call_date)} call <Cite href={pageLink(s.source_url, s.page)}>transcript p.{s.page}</Cite></div>
                    </div>
                    <div className="small muted" style={{ marginTop: 8 }}>{r.reason}</div>
                    {r.trail?.length > 0 && (
                      <ul className="trail">
                        {r.trail.map((e: Json, k: number) => (
                          <li key={k}><span className="ev">{e.event}</span><span>{callQuarter(e.call)} call{e.target ? ` · ${e.target}` : ""}{e.silent_calls ? ` · ${e.silent_calls} call(s) since` : ""}</span></li>
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
  // Real non-answers first; a request to repeat the question is not worth showing.
  const shown = judged.filter((j) => j.label !== "answered" && !/clarif/i.test(j.reason || ""))
    .sort((a, b) => (a.label === "dodged" ? 0 : 1) - (b.label === "dodged" ? 0 : 1));
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
        {l.revenue != null && <><span className="k">Quarter {s.lender ? "total income" : "revenue"}</span><span className="v">{fmtCr(l.revenue)}</span></>}
        {l.pat != null && <><span className="k">Quarter profit</span><span className="v">{fmtCr(l.pat)}</span></>}
        {l.gross_npa_pct != null && <><span className="k">Gross / net NPA</span><span className="v">{l.gross_npa_pct}% / {l.net_npa_pct}%</span></>}
        {s.roe_pct != null && <><span className="k">ROE</span><span className="v">{s.roe_pct}%</span></>}
        {s.roce_pct != null && !s.lender && <><span className="k">ROCE</span><span className="v">{s.roce_pct}%</span></>}
      </div>
    </>
  );
}

function Bank({ b, yearGrowth }: { b: Json; yearGrowth?: number | null }) {
  return (
    <>
      <Title meta={`quarter to ${fmtDay(b.quarter_end)}`}>Bank numbers</Title>
      <div className="glass card">
        <div className="kv">
          {b.nii != null && <><span className="k">Net interest income (NII)</span><span className="v">{fmtCr(b.nii)}{b.nii_yoy_pct != null ? <span className={signClass(b.nii_yoy_pct)}> {fmtPct(b.nii_yoy_pct)} YoY</span> : null}</span></>}
          {b.nim_approx_pct != null && <><span className="k">Margin on assets (≈ NIM)</span><span className="v">{b.nim_approx_pct}%</span></>}
          {b.gross_npa_pct != null && <><span className="k">Gross / net NPA</span><span className="v">{b.gross_npa_pct}% / {b.net_npa_pct}%</span></>}
          {b.deposits != null && <><span className="k">Deposits</span><span className="v">{fmtCr(b.deposits)}{b.deposit_growth_pct != null ? <span className={signClass(b.deposit_growth_pct)}> {fmtPct(b.deposit_growth_pct)} YoY</span>
            : yearGrowth != null ? <span className={signClass(yearGrowth)}> {fmtPct(yearGrowth)} last year</span> : null}</span></>}
        </div>
        <p className="faint small" style={{ marginBottom: 0 }}>{b.note} Not in the statement tables: {(b.missing || []).join(", ")}.</p>
      </div>
    </>
  );
}

function Trajectory({ t, lender }: { t: Json; lender?: boolean }) {
  const rows: Json[] = (t.annual || []).slice(-7);
  const c3 = t.cagr_pct?.["3y"] || {}, c5 = t.cagr_pct?.["5y"] || {};
  return (
    <>
      <Title meta="revenue bars · margin line">Trajectory</Title>
      <div className="glass card">
        <Bars label="Annual revenue with operating margin" metric={`${lender ? "Total income" : "Revenue"}, ₹ cr (bars) · operating margin (line)`}
          fmt={(v) => fmtCr(v)} lineName="margin"
          data={rows.map((r) => ({ x: `FY${r.year_end.slice(2, 4)}`, y: r.revenue, line: r.ebitda_margin_pct }))} />
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
          <svg viewBox="0 0 340 122" width="100%" role="img" aria-label="Operating cash flow compared with profit by year" className="chart">
            <defs>
              <linearGradient id="cash-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#9fe6c3" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.35" /></linearGradient>
              <linearGradient id="pat-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="rgba(255,255,255,0.42)" /><stop offset="1" stopColor="rgba(255,255,255,0.08)" /></linearGradient>
            </defs>
            {[0.5, 1].map((f) => <line key={f} x1="14" x2="326" y1={96 - f * 78} y2={96 - f * 78} stroke="rgba(255,255,255,0.06)" strokeDasharray="2 4" />)}
            <line x1="14" x2="326" y1="96" y2="96" stroke="rgba(255,255,255,0.14)" />
            {rows.map((r, i) => {
              const max = Math.max(...rows.flatMap((x) => [x.cfo || 0, x.pat || 0]), 1);
              const bw = 312 / rows.length, x0 = 14 + i * bw;
              const h1 = Math.max(((r.pat || 0) / max) * 78, 1), h2 = Math.max(((r.cfo || 0) / max) * 78, 1);
              return (
                <g key={r.year_end}>
                  <motion.rect x={x0 + bw * 0.14} width={bw * 0.32} rx="4" fill="url(#pat-g)"
                    initial={{ y: 96, height: 0 }} animate={{ y: 96 - h1, height: h1 }} transition={{ duration: 0.6, delay: i * 0.05 }} />
                  <motion.rect x={x0 + bw * 0.52} width={bw * 0.32} rx="4" fill="url(#cash-g)"
                    initial={{ y: 96, height: 0 }} animate={{ y: 96 - h2, height: h2 }} transition={{ duration: 0.6, delay: 0.1 + i * 0.05 }} />
                  <text x={x0 + bw / 2} y="114" textAnchor="middle" fontSize="10" fill="rgba(236,239,237,0.45)">FY{r.year_end.slice(2, 4)}</text>
                </g>
              );
            })}
          </svg>
        )}
        <div className="small muted">{c.reading || c.note}</div>
        {!c.lender && <div className="legend"><span><i className="dot-pat" />profit</span><span><i className="dot-cash" />operating cash flow</span></div>}
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
        <ul className="bullets">{bb.bull.map((x: Json, i: number) => <li key={i}><span className="up">▲</span><span>{rupee(x.text)} <span className="faint small">({x.cites.map((c: Json) => c.source).join(", ")})</span></span></li>)}</ul>
        <div className="small" style={{ fontWeight: 700, color: "var(--down)", letterSpacing: ".06em", marginTop: 12 }}>BEAR</div>
        <ul className="bullets">{bb.bear.map((x: Json, i: number) => <li key={i}><span className="down">▼</span><span>{rupee(x.text)} <span className="faint small">({x.cites.map((c: Json) => c.source).join(", ")})</span></span></li>)}</ul>
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
        {ts.map((t) => <Cite key={t.url} href={t.url}>{callQuarter(t.call)} call</Cite>)}
        {ar?.url && <Cite href={ar.url}>{ar.title}</Cite>}
        {d.sections?.snapshot?.source && <Cite href={d.sections.snapshot.source}>statement tables (screener.in)</Cite>}
        <div className="faint small" style={{ width: "100%" }}>Numbers from the statement tables; quotes checked word for word on the page cited. Built {fmtDay(d.started_at)}.</div>
      </div>
    </>
  );
}
