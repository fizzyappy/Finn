"""Dodged questions: did management answer what the analyst asked?

Each analyst question is paired with management's answer (transcripts.qa_pairs).
Gemini Flash-Lite labels each pair answered / partly / dodged with a reason of at
most 100 characters, and quotes the key words of the question and of the answer.
Both quotes must be found word for word in the transcript; a pair whose quotes do
not check out is left out of the score rather than guessed.
"""
from __future__ import annotations

from .. import documents, llm
from .transcripts import Transcript, qa_pairs

MAX_PAIRS = 30
SYSTEM = (
    "You judge whether company management answered analysts' questions on an earnings call. For each numbered "
    "pair: 'answered' = addressed what was asked (a number, a clear yes/no, or a specific explanation); 'partly' = "
    "addressed some of it or answered generally; 'dodged' = deflected, declined, or talked about something else. "
    "Declining to give guidance for stated policy reasons counts as 'partly'. reason: at most 100 characters, plain "
    "words. question_quote: copy the key question words exactly from the question. answer_quote: copy the most "
    "telling words exactly from the answer. Both quotes word for word, 5 to 30 words."
)
SCHEMA = {
    "type": "object",
    "properties": {"judgements": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "i": {"type": "integer"},
            "label": {"type": "string", "enum": ["answered", "partly", "dodged"]},
            "reason": {"type": "string"},
            "question_quote": {"type": "string"},
            "answer_quote": {"type": "string"},
        },
        "required": ["i", "label", "reason", "question_quote", "answer_quote"]}}},
    "required": ["judgements"],
}


def judge(tr: Transcript) -> dict:
    pairs = qa_pairs(tr.turns)[:MAX_PAIRS]
    out = {"call": tr.date, "url": tr.url, "pairs_found": len(qa_pairs(tr.turns)), "judged": [], "unverified": 0}
    if not pairs:
        out["note"] = "no analyst questions found in this transcript"
        return out
    prompt = "\n\n".join(f"#{i}\nQUESTION ({p['analyst']}): {p['question'][:900]}\nANSWER ({', '.join(p['answered_by'])}): "
                         f"{p['answer'][:1500]}" for i, p in enumerate(pairs))
    res = llm.router().complete("dodged", prompt, system=SYSTEM, tier="lite", schema=SCHEMA, max_tokens=6000)
    if not res or not isinstance(res.data, dict):
        out["note"] = "model unavailable" if not llm.router().available else "no usable answer"
        return out
    for j in res.data.get("judgements") or []:
        i = j.get("i")
        if not isinstance(i, int) or not 0 <= i < len(pairs):
            continue
        p = pairs[i]
        qq, aq = (j.get("question_quote") or "").strip(), (j.get("answer_quote") or "").strip()
        q_ok = qq and documents.quote_key(qq) in documents.quote_key(p["question"])
        a_ok = aq and documents.quote_key(aq) in documents.quote_key(p["answer"])
        q_page = documents.find_quote(tr.pages, qq) if q_ok else None
        a_page = documents.find_quote(tr.pages, aq) if a_ok else None
        if not (q_page and a_page):
            out["unverified"] += 1
            continue
        out["judged"].append({"analyst": p["analyst"], "answered_by": p["answered_by"], "label": j["label"],
                              "reason": (j.get("reason") or "")[:100], "question_quote": qq, "question_page": q_page,
                              "answer_quote": aq, "answer_page": a_page})
    n = len(out["judged"])
    out["counts"] = {k: sum(1 for x in out["judged"] if x["label"] == k) for k in ("answered", "partly", "dodged")}
    out["summary"] = f"questions dodged: {out['counts']['dodged']} of {n}" if n else "no verified judgements"
    return out
