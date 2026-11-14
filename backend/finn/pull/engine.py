"""Research on demand: one call -> a cited research view for any listed company.

Stages (reported to the app as they happen, so a cold start shows progress):
  resolving -> fetching tables -> reading transcripts -> checking promises ->
  judging answers -> reading annual report -> writing -> done
Table sections are published first (seconds); transcript sections follow.
Results are cached by (ticker, date of the newest source document), so a company
is only re-read when it files something new.

Graceful states: no transcripts found, AI busy (free-tier limit), too early.
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime
from typing import Callable

from .. import fundamentals, llm, symbols
from ..store import store
from . import business, dodged, narrative, promises, tables, transcripts

AR_BUDGET_SECONDS = 240
_ar_pool = __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=2)
FuturesTimeout = __import__("concurrent.futures").futures.TimeoutError

STAGES = ["resolving", "fetching tables", "reading transcripts", "checking promises", "judging answers",
          "reading annual report", "writing", "done"]


def _ai_busy(since: float) -> bool:
    conn = store().conn
    conn.executescript(llm.SCHEMA_SQL)
    row = conn.execute("SELECT COUNT(*) FROM llm_log WHERE ts >= ? AND ok = 0 AND (error LIKE '%429%' OR "
                       "error LIKE '%RESOURCE_EXHAUSTED%')", (since,)).fetchone()
    return bool(row and row[0])


def report_card(ledger: dict | None, dodged_calls: list[dict]) -> dict:
    card: dict = {"evidence": []}
    if ledger:
        c = ledger["counts"]
        card["promises_kept"] = ledger["kept_of_measurable"]
        card["promise_counts"] = c
        card["topics_dropped"] = [f"{r['metric'].replace('_', ' ')} {r['horizon']} ({r['target']})"
                                  for r in ledger["promises"] if r["verdict"] == "Quietly dropped"]
        for r in ledger["promises"]:
            if r["verdict"] in ("Kept", "Missed", "Partly", "Quietly dropped"):
                s = r["said"]
                card["evidence"].append({"claim": f"{r['verdict']}: {r['metric'].replace('_', ' ')} {r['horizon']} "
                                                  f"target {r['target']}", "quote": s["quote"], "page": s["page"],
                                         "url": s["source_url"], "call": s["call_date"]})
    judged = [j for d in dodged_calls for j in d.get("judged", [])]
    if judged:
        n_d = sum(1 for j in judged if j["label"] == "dodged")
        n_p = sum(1 for j in judged if j["label"] == "partly")
        card["questions_dodged"] = f"{n_d} of {len(judged)}"
        card["questions_partly_answered"] = f"{n_p} of {len(judged)}"
        for j in judged:
            if j["label"] == "dodged":
                card["evidence"].append({"claim": f"Dodged: {j['reason']}", "quote": j["question_quote"],
                                         "page": j["question_page"], "answer_quote": j["answer_quote"],
                                         "answer_page": j["answer_page"]})
    return card


def research(ticker: str, *, refresh: bool = False, n_transcripts: int = 5,
             progress: Callable[[str, dict], None] | None = None) -> dict:
    t0 = time.time()
    out: dict = {"ticker": ticker.upper(), "started_at": datetime.now().isoformat(timespec="seconds"),
                 "states": [], "sections": {}}

    def step(stage: str):
        out["stage"] = stage
        if progress:
            progress(stage, out)

    step("resolving")
    inst = symbols.resolve(ticker)
    out["instrument"] = inst.to_dict()
    step("fetching tables")
    tb = tables.build(inst.screener_key)
    out["name"] = tb["name"]
    out["sections"].update({k: tb[k] for k in ("snapshot", "trajectory", "balance_sheet", "cash_quality")})
    out["data_as_of"] = tb["data_as_of"]
    # Cache key: the newest source document date.
    cands = fundamentals.transcript_candidates(inst.screener_key)
    newest = max([c.get("date") or "" for c in cands] + [tb["snapshot"].get("latest_quarter") or ""])
    key = f"{out['ticker']}|{newest}"
    if not refresh:
        hit = store().get("research", key)
        if hit:
            res = hit[0]
            res["from_cache"] = True
            step("done")
            return res
    step("reading transcripts")
    trs, notes = transcripts.load(inst.screener_key, n=n_transcripts)
    out["transcripts"] = [{"call": t.date, "url": t.url, "turns": len(t.turns)} for t in trs]
    out["transcript_notes"] = notes
    led, dodged_calls = None, []
    if not trs:
        out["states"].append({"state": "no_transcripts",
                              "message": "No earnings-call transcripts were found for this company, so the promise "
                                         "ledger and dodged-question check are not available."})
    else:
        step("checking promises")
        led = promises.ledger(trs, fundamentals.get_fundamentals(inst.screener_key).data)
        out["sections"]["promise_ledger"] = led
        if led["counts"]["Too early"] and not (led["counts"]["Kept"] + led["counts"]["Missed"] + led["counts"]["Partly"]):
            out["states"].append({"state": "too_early", "message": "Management's targets are for periods not yet "
                                                                   "reported; verdicts will come with the next results."})
        step("judging answers")
        dodged_calls = [dodged.judge(t) for t in trs[:2]]
        out["sections"]["dodged_questions"] = dodged_calls
        out["sections"]["narrative_vs_numbers"] = narrative.narrative_vs_numbers(tb, trs[0])
    step("reading annual report")
    fut = _ar_pool.submit(business.build, inst.screener_key)
    try:
        out["sections"]["business_snapshot"] = fut.result(timeout=AR_BUDGET_SECONDS)
    except FuturesTimeout:
        out["sections"]["business_snapshot"] = {
            "status": "timeout", "note": f"the annual report took longer than {AR_BUDGET_SECONDS // 60} minutes to read; "
                                         "segments will appear on the next run (the download continues in the background)"}
    except Exception as e:  # noqa: BLE001
        out["sections"]["business_snapshot"] = {"status": "error", "note": f"{type(e).__name__}: {str(e)[:120]}"}
    step("writing")
    facts = narrative.fact_pool(tb, led, dodged_calls)
    out["sections"]["facts"] = facts
    out["sections"]["bull_bear"] = narrative.bull_bear(facts, tb["name"])
    out["sections"]["report_card"] = report_card(led, dodged_calls)
    if _ai_busy(t0):
        out["states"].append({"state": "ai_busy", "message": "The free AI tier hit its limit during this run; some "
                                                             "sections may be incomplete. Try again in a few minutes."})
    out["llm_usage"] = llm.usage(since=t0)
    out["built_in_seconds"] = round(time.time() - t0, 1)
    out["from_cache"] = False
    if not any(s["state"] == "ai_busy" for s in out["states"]):
        store().put("research", key, out, "pull engine")
    step("done")
    return out


# ------------------------------------------------------------------ jobs (cold start with progress)
import threading                     # noqa: E402
import uuid                          # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

_jobs: dict[str, dict] = {}
_pool = ThreadPoolExecutor(max_workers=1)    # one at a time: protects the free-tier quota
_lock = threading.Lock()


def start(ticker: str, refresh: bool = False) -> dict:
    with _lock:
        for j in _jobs.values():
            if j["ticker"] == ticker.upper() and j["status"] in ("queued", "running"):
                return j
        jid = uuid.uuid4().hex[:12]
        job = {"id": jid, "ticker": ticker.upper(), "status": "queued", "stage": None, "stages": STAGES,
               "partial": None, "result": None, "error": None, "created": time.time()}
        _jobs[jid] = job

    def progress(stage: str, snapshot: dict):
        job["stage"] = stage
        job["partial"] = {k: snapshot.get(k) for k in ("ticker", "name", "instrument", "sections", "states")}

    def run():
        job["status"] = "running"
        try:
            job["result"] = research(ticker, refresh=refresh, progress=progress)
            job["status"] = "done"
        except Exception as e:  # noqa: BLE001
            job["status"], job["error"] = "failed", f"{type(e).__name__}: {e}"
            job["trace"] = traceback.format_exc(limit=4)
    _pool.submit(run)
    return job


def status(job_id: str) -> dict | None:
    j = _jobs.get(job_id)
    if not j:
        return None
    done = STAGES.index(j["stage"]) if j["stage"] in STAGES else -1
    return {**{k: v for k, v in j.items() if k not in ("result", "trace")},
            "progress_pct": round((done + 1) / len(STAGES) * 100)}


def result(job_id: str) -> dict | None:
    j = _jobs.get(job_id)
    return j and j.get("result")


def vs_guidance(ticker: str, quarter_end: str) -> list[dict]:
    """Hook for the push Results card: open targets covering the quarter just reported
    (from the cached research, if the company has been researched)."""
    for (k,) in store().conn.execute("SELECT key FROM cache WHERE ns='research' AND key LIKE ? ORDER BY fetched_at DESC",
                                     (f"{ticker.upper()}|%",)).fetchall():
        hit = store().get("research", k)
        led = hit and hit[0]["sections"].get("promise_ledger")
        if led:
            return promises.vs_guidance(led, quarter_end)
    return []
