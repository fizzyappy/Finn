"""Ask about this company: answers only from that company's verified evidence.

Evidence = the facts Python computed from the statement tables, management's
promises with their verified quotes and verdicts, verified question/answer quotes
from the calls, story-vs-numbers quotes and the segment table. Nothing else: no
outside knowledge, no web.

The model (Gemini Flash, falling back to Flash-Lite) must cite evidence ids. Python
then checks the answer: it must cite real evidence, every number in it must appear
in the cited evidence, and it must not praise without numbers. If the evidence does
not cover the question, or a check fails, FINN says so instead of guessing.
"""
from __future__ import annotations

import re

from .. import llm
from ..push.summarize import unsupported_adjectives

SYSTEM = (
    "You answer an investor's question about one Indian listed company using ONLY the numbered evidence given. "
    "Do not use outside knowledge. If the evidence does not answer the question, set covered to false and say "
    "briefly what is missing. Otherwise answer in at most 3 short sentences, copy numbers exactly as they appear in "
    "the evidence, and list every evidence id you used. No advice, no price targets, no adjectives without numbers."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "covered": {"type": "boolean"},
        "answer": {"type": "string"},
        "cites": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["covered", "answer", "cites"],
}
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def evidence(research: dict) -> list[dict]:
    """Numbered evidence from a finished research result, each with its source."""
    S = research.get("sections") or {}
    ev: list[dict] = []

    def add(text: str, source: str, url: str | None = None, page: int | None = None):
        ev.append({"id": f"E{len(ev) + 1}", "text": text, "source": source, "url": url, "page": page})
    for f in S.get("facts") or []:
        add(f["text"], f["source"])
    led = S.get("promise_ledger") or {}
    for r in led.get("promises") or []:
        s = r["said"]
        add(f"{r['verdict']}: {r['metric'].replace('_', ' ')} {r['horizon']} target {r['target']}"
            + (f" ({r['scope']})" if r.get("scope") and r["scope"] != "company" else "")
            + f". Management said on {s['call_date'][:7]}: \"{s['quote']}\". {r['reason']}",
            "promise ledger / call transcript", s.get("source_url"), s.get("page"))
    for d in S.get("dodged_questions") or []:
        for j in d.get("judged") or []:
            add(f"Analyst {j['analyst']} asked: \"{j['question_quote']}\" Management answered: \"{j['answer_quote']}\" "
                f"(judged {j['label']})", f"call transcript {d['call'][:7]}", d.get("url"), j.get("answer_page"))
    for x in S.get("narrative_vs_numbers") or []:
        add(f"Management said: \"{x['quote']}\" while {x['numbers']}", "call transcript + quarterly P&L", x.get("url"), x.get("page"))
    b = S.get("business_snapshot") or {}
    if b.get("segments"):
        add("Segments (" + (b.get("status") or "") + "): " + "; ".join(
            f"{s['name']} {s['mix_pct']}% of revenue" + (f", growth {s['growth_pct']}%" if s.get("growth_pct") is not None else "")
            for s in b["segments"]), "annual report", (b.get("source") or {}).get("url"), (b.get("pages") or [None])[0])
    return ev


def check(answer: str, cites: list[str], ev: dict[str, dict]) -> str | None:
    """None if the answer stands on its cited evidence, else why it is refused."""
    used = [ev[c] for c in cites if c in ev]
    if not used:
        return "it did not cite any evidence"
    pool = " ".join(e["text"] for e in used).replace(",", "")
    missing = [n for n in _NUM.findall(answer) if n.replace(",", "") not in pool]
    if missing:
        return f"it used numbers not in the evidence ({', '.join(missing[:3])})"
    if unsupported_adjectives(answer):
        return "it used praise words without numbers"
    return None


def ask(research: dict, question: str) -> dict:
    question = (question or "").strip()[:300]
    if len(question) < 4:
        return {"status": "invalid", "answer": "Please ask a question about the company."}
    ev = evidence(research)
    if not ev:
        return {"status": "no_evidence", "answer": "FINN has no verified evidence for this company yet."}
    prompt = f"Company: {research.get('name')} ({research.get('ticker')})\nQuestion: {question}\n\nEvidence:\n" + \
             "\n".join(f"{e['id']}: {e['text']} [source: {e['source']}]" for e in ev)
    res = llm.router().complete("ask", prompt, system=SYSTEM, tier="flash", schema=SCHEMA, max_tokens=1500)
    if not res or not isinstance(res.data, dict):
        return {"status": "ai_busy", "answer": "The AI is busy right now (free tier). Try again in a minute."}
    by_id = {e["id"]: e for e in ev}
    if not res.data.get("covered"):
        return {"status": "not_covered", "answer": "FINN's sources for this company don't answer that. "
                + (res.data.get("answer") or "")[:200], "model": res.model}
    why = check(res.data.get("answer") or "", res.data.get("cites") or [], by_id)
    if why:
        return {"status": "refused", "answer": f"FINN won't answer this one: {why}, so the answer could be wrong.",
                "model": res.model}
    return {"status": "answered", "answer": res.data["answer"].strip(), "model": res.model, "cached": res.cached,
            "citations": [{k: by_id[c][k] for k in ("id", "text", "source", "url", "page")} for c in res.data["cites"] if c in by_id]}
