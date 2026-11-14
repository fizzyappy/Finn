"""Dodged questions: did management answer what the analyst asked?

Each analyst question is paired with management's answer (transcripts.qa_pairs).
Gemini Flash-Lite labels each pair answered / partly / dodged with a reason of at
most 100 characters, and quotes the key words of the question and of the answer.
Both quotes must be found word for word in the transcript; a pair whose quotes do
not check out is left out of the score rather than guessed.
"""
from __future__ import annotations

import re

from .. import documents, llm
from .transcripts import Transcript, qa_pairs

MAX_PAIRS = 30
SYSTEM = (
    "You judge whether company management answered analysts' questions on an earnings call. Be conservative: "
    "most answers are 'answered'. For each numbered pair: 'answered' = addressed what was asked (a number, a clear "
    "yes/no, or a specific explanation). 'partly' = answered only part, or only in general terms. 'dodged' ONLY for a "
    "clear non-answer: an explicit refusal ('we don't comment', 'can't share'), a promise to come back later instead "
    "of answering, a deflection to a different topic, or no number when a specific number was asked. Asking the "
    "analyst to repeat or clarify is NOT a dodge. If unsure, do not say 'dodged'. reason: at most 100 characters, "
    "plain words. question_quote: copy the key question words exactly. answer_quote: copy, word for word, the words "
    "that show your label (for 'dodged', the refusal or deflection itself). Both quotes 5 to 30 words."
)
# Python's own check on every "dodged" label: the quoted answer must show the
# non-answer, or a number was asked and the whole answer contains none.
DEFLECT = re.compile(
    r"\b(not|won't|wouldn't|cannot|can't|don't|do not|unable to|not able to)\s+(be able to\s+)?(give|share|comment|disclose|"
    r"provide|guide|talk|get into|discuss|spell out|quantify|reveal|specify)|no (specific )?comments?|come back to you|"
    r"get back to you|revert|take (it|this) offline|not in a position|too early to (say|comment)|prefer not|"
    r"beyond the scope|we don't guide|not going to (give|share|comment)|let me not|"
    r"(do not|don't) have any (specific |further )?(comments?|update|number|details|clarity)|"
    r"(nothing|anything) (more|further) to (say|add|share)|refrain from|rather not", re.I)
CLARIFY = re.compile(r"\b(sorry|could you (please )?repeat|can you repeat|didn't (catch|get)|which (one|program)|you mean)\b", re.I)
NUMBER_ASKED = re.compile(r"\bhow (much|many)|what (is|was|would be|will be) the (number|size|quantum|amount|figure|guidance|"
                          r"margin|growth)|what percentage|\bquantify|by when|what kind of (number|growth)|\brange\b", re.I)


def confirm_dodge(question: str, answer: str, answer_quote: str) -> tuple[str, str | None]:
    """Keep 'dodged' only when the evidence shows it; else downgrade to 'partly'."""
    if CLARIFY.search(answer_quote) and not DEFLECT.search(answer_quote):
        return "partly", "asked to clarify the question (not a dodge)"
    if DEFLECT.search(answer_quote):
        return "dodged", None
    if NUMBER_ASKED.search(question) and not re.search(r"\d", answer):
        return "dodged", None
    return "partly", "no refusal or deflection shown in the quoted answer"
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
        label, reason = j["label"], (j.get("reason") or "")[:100]
        if label == "dodged":
            label, why_not = confirm_dodge(p["question"], p["answer"], aq)
            if why_not:
                out.setdefault("downgraded", 0)
                out["downgraded"] += 1
                reason = f"{reason} ({why_not})"[:160]
        out["judged"].append({"analyst": p["analyst"], "answered_by": p["answered_by"], "label": label,
                              "reason": reason, "question_quote": qq, "question_page": q_page,
                              "answer_quote": aq, "answer_page": a_page})
    n = len(out["judged"])
    out["counts"] = {k: sum(1 for x in out["judged"] if x["label"] == k) for k in ("answered", "partly", "dodged")}
    out["summary"] = f"questions dodged: {out['counts']['dodged']} of {n}" if n else "no verified judgements"
    return out
