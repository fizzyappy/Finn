"""Measure the classifier and the 3-way treatment against hand-labelled real filings.

fixtures/labelled_filings.json  90 filings of the 18 demo holdings (category + treatment labels)
fixtures/heldout_filings.json   34 filings of other companies from the RSS feeds (category labels)
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .. import fundamentals
from . import classify, materiality, portfolio

FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def load(name: str) -> list[dict]:
    return json.loads((FIX / name).read_text(encoding="utf-8"))["items"]


def market_caps(symbols: list[str]) -> dict[str, float | None]:
    out = {}
    for s in symbols:
        try:
            vals = fundamentals.get_fundamentals(s).data["top_ratios"].get("Market Cap", {}).get("values") or [None]
            out[s] = vals[0]
        except Exception:  # noqa: BLE001
            out[s] = None
    return out


def evaluate(items: list[dict], *, use_llm: bool, p: portfolio.Portfolio | None = None,
             mcaps: dict | None = None) -> dict:
    cat_ok = tr_ok = tr_n = 0
    confusion: Counter = Counter()
    errors = []
    for it in items:
        c = classify.classify(it, use_llm=use_llm) if use_llm else classify.rule_classify(it)[0]
        row = {"company": it.get("symbol") or it.get("company"), "subject": (it.get("subject") or "")[:90],
               "want": it["label_category"], "got": c.category, "method": c.method}
        cat_ok += c.category == it["label_category"]
        if "label_treatment" in it and p is not None:
            sym = it["symbol"]
            sc = materiality.score(it, c, weight=p.weights.get(sym), mcap_cr=(mcaps or {}).get(sym), prefs=p.preferences)
            tr_n += 1
            tr_ok += sc.treatment == it["label_treatment"]
            confusion[f"{it['label_treatment']} -> {sc.treatment}"] += 1
            row |= {"want_treatment": it["label_treatment"], "got_treatment": sc.treatment, "score": sc.value}
        if row["want"] != row["got"] or row.get("want_treatment") != row.get("got_treatment"):
            errors.append(row)
    n = len(items)
    return {"n": n, "category_accuracy": round(cat_ok / n, 3) if n else None,
            "treatment_accuracy": round(tr_ok / tr_n, 3) if tr_n else None,
            "treatment_confusion": dict(confusion), "errors": errors}


def run(use_llm: bool = True) -> dict:
    p = portfolio.load()
    labelled = load("labelled_filings.json")
    mcaps = market_caps(p.symbols)
    return {
        "portfolio_set": evaluate(labelled, use_llm=use_llm, p=p, mcaps=mcaps),
        "heldout_rules_only": evaluate(load("heldout_filings.json"), use_llm=False),
        "heldout_with_llm": evaluate(load("heldout_filings.json"), use_llm=use_llm) if use_llm else None,
    }
