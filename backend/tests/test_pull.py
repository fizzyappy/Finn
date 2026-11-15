"""Pull engine: deterministic parts, offline."""
from __future__ import annotations

import json
from datetime import date

import pytest

from finn import documents, llm
from finn.pull import business, engine, narrative, periods, promises, tables, transcripts
from finn.pull.promises import Promise


# ------------------------------------------------------------------ fiscal periods
@pytest.mark.parametrize("text,call,label,end", [
    ("FY27", date(2026, 10, 23), "FY27", "2027-03-31"),
    ("H2 FY27", date(2026, 10, 23), "H2FY27", "2027-03-31"),
    ("this year", date(2026, 10, 23), "FY27", "2027-03-31"),
    ("this year", date(2026, 4, 20), "FY27", "2027-03-31"),       # a Q4 call talks about the new year
    ("next year", date(2026, 10, 23), "FY28", "2028-03-31"),
    ("Q3", date(2026, 10, 23), "Q3FY27", "2026-12-31"),
    ("March '26", date(2025, 7, 28), "FY26", "2026-03-31"),
    ("March ‘26", date(2025, 7, 28), "FY26", "2026-03-31"),
    ("full year FY2028", date(2026, 10, 23), "FY28", "2028-03-31"),
    # Found by the hand spot-check of HAL's ledger:
    ("FY24-25", date(2024, 5, 20), "FY25", "2025-03-31"),
    ("current financial year '26-'27", date(2026, 5, 20), "FY27", "2027-03-31"),
    ("FY '23 and FY '24", date(2023, 5, 20), "FY24", "2024-03-31"),
    ("full financial year", date(2022, 11, 10), "FY23", "2023-03-31"),
])
def test_horizons(text, call, label, end):
    h = periods.resolve(text, call)
    assert h.label == label and h.end.isoformat() == end


def test_multi_year_and_open_horizons():
    h = periods.resolve("over five years", date(2026, 5, 20))
    assert h.kind == "multi" and h.fy == 2031
    assert periods.resolve("by FY30", date(2026, 10, 1)).kind == "multi"
    assert periods.resolve("medium term", date(2026, 10, 1)).end is None


def test_quarter_maths():
    assert periods.quarter_of(date(2026, 9, 30)) == (2027, 2)
    assert periods.quarter_end(2027, 4).isoformat() == "2027-03-31"
    assert periods.discussed_quarter(date(2026, 10, 23)) == (2027, 2)


# ------------------------------------------------------------------ transcripts
PAGES = [
    "Company Ltd Earnings Call\nCORPORATE PARTICIPANTS:\nAsha Rao\nChief Executive Officer\nVikram Shah\nChief Financial Officer\n",
    "Company Ltd Earnings Call\nModerator: Good evening and welcome. I now hand over to Asha Rao.\n"
    "Asha Rao: Thank you. Revenue grew well this quarter. We expect revenue growth of 12% to 14% in FY27.\n"
    "Moderator: The first question is from the line of Rahul Mehta from Alpha Securities.\n"
    "Rahul Mehta: What is the margin outlook for next year? And how is demand?\n",
    "Company Ltd Earnings Call\nVikram Shah: We aim to keep EBITDA margin at 18% for FY27. Demand is steady.\n"
    "Moderator: The next question is from Neha Jain from Beta Capital.\n"
    "Neha Jain: Can you share the capex plan?\n"
    "Asha Rao: We will not give a number today. We will update later.\n",
]


def test_split_turns_and_roles():
    turns = transcripts.split_turns(PAGES)
    roles = {t.speaker: t.role for t in turns}
    assert roles == {"Moderator": "moderator", "Asha Rao": "management", "Rahul Mehta": "analyst",
                     "Vikram Shah": "management", "Neha Jain": "analyst"}
    assert all("Company Ltd Earnings Call" not in t.text for t in turns)    # running header removed
    pairs = transcripts.qa_pairs(turns)
    assert [(p["analyst"], p["answered_by"]) for p in pairs] == [("Rahul Mehta", ["Vikram Shah"]), ("Neha Jain", ["Asha Rao"])]
    assert pairs[0]["q_page"] == 2 and pairs[0]["a_page"] == 3


def test_document_labels_are_not_speakers():
    pages = ["Sensitivity: Internal\nAsha Rao: Hello all. We will grow.\nAsha Rao: Yes we will.\n"
             "Rahul Mehta: Why? What is the plan?\nSensitivity: Internal\n"] * 2
    assert "Sensitivity" not in {t.speaker for t in transcripts.split_turns(pages)}


# ------------------------------------------------------------------ quotes
def test_quote_check_ignores_pdf_spacing_but_nothing_else():
    pages = ["our last gui dance was 1.5% to 3%.", "Margins remain at 21%."]
    assert documents.find_quote(pages, "our last guidance was 1.5% to 3%") == 1
    assert documents.find_quote(pages, "our last guidance was 2% to 3%") is None
    assert documents.find_quote(pages, "Margins remain at 21%") == 2


# ------------------------------------------------------------------ promises: extraction with a fake model
class _Client:
    def __init__(self, payload):
        self.payload = payload

        class M:
            def generate_content(_, model, contents, config):
                class R:
                    text = json.dumps(payload)
                    usage_metadata = None
                return R()
        self.models = M()


@pytest.fixture
def fake_router(monkeypatch):
    monkeypatch.setattr(llm, "MIN_GAP_SECONDS", {"lite": 0, "flash": 0})

    def use(payload):
        llm.use_router(llm.Router(client=_Client(payload)))
    yield use
    llm.use_router(None)


def _transcript():
    turns = transcripts.split_turns(PAGES)
    return transcripts.Transcript("https://www.bseindia.com/t.pdf", "2026-10-31", "", PAGES, turns)


def test_extract_verifies_and_repairs_quotes(fake_router):
    tr = _transcript()
    cands = promises.candidates(tr)
    texts = [c["sentence"] for c in cands]
    assert any("12% to 14%" in t for t in texts) and any("18%" in t for t in texts)
    i_rev = next(i for i, t in enumerate(texts) if "12% to 14%" in t)
    i_mar = next(i for i, t in enumerate(texts) if "18%" in t)
    fake_router({"promises": [
        {"i": i_rev, "metric": "revenue_growth", "target_low": 12, "target_high": 14, "unit": "pct_growth",
         "horizon": "FY27", "scope": "company", "firmness": "firm", "quote": "revenue growth of 12% to 14% in FY27"},
        {"i": i_mar, "metric": "ebitda_margin", "target_low": 18, "unit": "pct_margin", "horizon": "FY27",
         "scope": "company", "firmness": "firm", "quote": "EBITDA margin of 20% (invented)"},
        {"i": 99, "metric": "pat", "unit": "rs_crore", "horizon": "FY27", "scope": "company", "firmness": "firm", "quote": "x"},
    ]})
    ps, st = promises.extract(tr)
    assert st["extracted"] == 3 and st["verified"] == 2 and st["dropped"] == 1 and st["quote_replaced"] == 1
    rev = next(p for p in ps if p.metric == "revenue_growth")
    assert rev.page == 2 and rev.horizon == "FY27" and rev.quote_method == "model"
    mar = next(p for p in ps if p.metric == "ebitda_margin")
    assert mar.quote_method == "source sentence" and "18%" in mar.quote and mar.page == 3


# ------------------------------------------------------------------ promises: measure, verdict, trail
F = {
    "annual": {"2026-03-31": {"revenue": 1150, "ebitda": 230, "pat": 120, "depreciation": 30},
               "2025-03-31": {"revenue": 1000, "ebitda": 190, "pat": 100, "depreciation": 25}},
    "quarterly": {"2026-09-30": {"revenue": 300}},
    "balance_sheet": {"2026-03-31": {"borrowings": 50, "equity_capital": 10, "reserves": 590},
                      "2025-03-31": {"borrowings": 80, "equity_capital": 10, "reserves": 490}},
}


def _p(metric, unit, lo, hi=None, horizon="FY26", call="2025-07-31", scope="company", basis=""):
    h = periods.resolve(horizon, date.fromisoformat(call))
    return Promise(metric, unit, lo, hi, basis, horizon, h.label, h.end.isoformat() if h.end else None, "firm",
                   "quote", 1, "CEO", call, "u", scope=scope)


def test_measure_in_the_promise_unit():
    assert promises.measure(_p("revenue_growth", "pct_growth", 12), F)["actual"] == 15.0
    assert promises.measure(_p("ebitda_margin", "pct_margin", 18), F)["actual"] == 20.0
    assert promises.measure(_p("ebit_margin", "pct_margin", 18), F)["actual"] == round(200 / 1150 * 100, 1)
    assert promises.measure(_p("roe", "pct_margin", 15), F)["actual"] == round(120 / 550 * 100, 1)
    assert promises.measure(_p("revenue_growth", "pct_growth", 12, basis="constant currency"), F)["status"] == "not_measurable"
    assert promises.measure(_p("ebit_margin", "pct_margin", 8, scope="core E&C"), F)["status"] == "not_measurable"
    assert promises.measure(_p("revenue_growth", "pct_growth", 12, horizon="FY28"), F)["status"] == "too_early"
    assert promises.measure(_p("order_inflow", "pct_growth", 10), F)["status"] == "not_measurable"


def test_spot_check_fixes():
    # constant-currency words in the sentence, not the quote (Infosys)
    p = _p("revenue_growth", "pct_growth", 3, 3.5)
    p.quote, p.sentence = "3% to 3.5%", "The new revenue growth guidance is 3% to 3.5% growth in constant currency."
    assert promises.measure(p, F)["status"] == "not_measurable"
    # far above target: probably another scope, not scored (Titan)
    assert promises.verdict(_p("revenue_growth", "pct_growth", 13, 14), 44.9)[0] == "not_measurable"
    # a margin target restated under another margin label is not "dropped" (L&T)
    calls = ["2025-07-31", "2025-10-31", "2026-01-31"]
    ps = [_p("ebit_margin", "pct_margin", 8.3, 8.5, call="2025-07-31"),
          _p("ebitda_margin", "pct_margin", 8.5, call="2026-01-31")]
    ebit = next(t for t in promises.trails(ps, calls) if t["metric"] == "ebit_margin")
    assert ebit["events"][-1]["event"] == "not repeated yet"
    # a segment target is not a "cut" of the company target (HAL)
    seg = [_p("revenue_growth", "pct_growth", 10, 11, horizon="FY25", call="2023-05-31"),
           _p("revenue_growth", "pct_growth", 9, 10, horizon="FY25", call="2024-05-31", scope="repair and overhaul")]
    tr = promises.trails(seg, ["2023-05-31", "2024-05-31"])
    assert len(tr) == 2 and all(e["event"] != "cut" for t in tr for e in t["events"])
    # the same 8.5% target labelled 'company' in one call and by segment in another is the segment's (L&T)
    a = _p("ebitda_margin", "pct_margin", 8.5, call="2025-10-31")
    b = _p("ebit_margin", "pct_margin", 8.5, call="2026-01-31", scope="Projects & Manufacturing")
    assert promises.harmonise_scopes([a, b]) == 1 and a.scope == "Projects & Manufacturing"


def test_verdicts_are_decided_by_numbers():
    assert promises.verdict(_p("revenue_growth", "pct_growth", 12, 14), 13.0)[0] == "kept"
    assert promises.verdict(_p("revenue_growth", "pct_growth", 12, 14), 11.6)[0] == "kept"      # within 0.5 pt
    assert promises.verdict(_p("revenue_growth", "pct_growth", 12, 14), 10.5)[0] == "partly"
    assert promises.verdict(_p("revenue_growth", "pct_growth", 15), 11.8)[0] == "missed"
    assert promises.verdict(_p("net_debt", "rs_crore", 0), 0)[0] == "kept"
    assert promises.verdict(_p("net_debt", "rs_crore", 100), 150)[0] == "missed"


def test_revision_trail_and_quiet_drop():
    calls = ["2025-07-31", "2025-10-31", "2026-01-31"]
    ps = [_p("revenue_growth", "pct_growth", 15, call="2025-07-31"),
          _p("revenue_growth", "pct_growth", 12, 13, call="2025-10-31"),
          _p("ebitda_margin", "pct_margin", 20, call="2025-07-31")]
    tr = {(t["metric"]): t for t in promises.trails(ps, calls)}
    assert [e["event"] for e in tr["revenue_growth"]["events"]] == ["set", "cut", "not repeated yet"]
    assert [e["event"] for e in tr["ebitda_margin"]["events"]] == ["set", "quietly dropped"]


def test_ledger_end_to_end_with_fake_model(fake_router):
    tr = _transcript()
    texts = [c["sentence"] for c in promises.candidates(tr)]
    i = next(i for i, t in enumerate(texts) if "12% to 14%" in t)
    fake_router({"promises": [{"i": i, "metric": "revenue_growth", "target_low": 12, "target_high": 14, "unit": "pct_growth",
                               "horizon": "FY26", "scope": "company", "firmness": "firm", "quote": "revenue growth of 12% to 14%"}]})
    led = promises.ledger([tr], F)
    row = led["promises"][0]
    assert row["verdict"] == "Kept" and row["actual"] == 15.0 and led["kept_of_measurable"] == "1 of 1"
    assert promises.vs_guidance({"promises": [{**row, "verdict": "Too early"}]}, "2025-12-31")[0]["target"] == "12-14%"


# ------------------------------------------------------------------ narrative and bull/bear checks
def test_bullets_must_stand_on_cited_facts():
    facts = {"F1": {"id": "F1", "text": "5y revenue CAGR 12.2%, profit CAGR 8.7%", "source": "P&L"}}
    assert narrative.check_bullet({"text": "Revenue compounded 12.2% a year over 5 years.", "cites": ["F1"]}, facts) is None
    assert "not in cited" in narrative.check_bullet({"text": "Revenue CAGR 15%.", "cites": ["F1"]}, facts)
    assert narrative.check_bullet({"text": "Revenue grew 12.2%.", "cites": ["F9"]}, facts) == "cites no real fact"
    assert narrative.check_bullet({"text": "Strong growth story.", "cites": ["F1"]}, facts) == "no number"


def test_narrative_vs_numbers_flags_upbeat_words_when_numbers_fell():
    tb = {"trajectory": {"quarters": [{"quarter_end": f"q{i}", "revenue": 100, "pat": 10, "ebitda_margin_pct": 20} for i in range(4)]
                         + [{"quarter_end": "2026-09-30", "revenue": 90, "pat": 11, "ebitda_margin_pct": 21}]}}
    tr = _transcript()
    tr.turns[1].text = "Revenue growth was strong this quarter across markets. We will grow more."
    tr.pages[1] += "\nRevenue growth was strong this quarter across markets."
    out = narrative.narrative_vs_numbers(tb, tr)
    assert len(out) == 1 and out[0]["metric"] == "revenue" and "-10.0%" in out[0]["numbers"]


def test_fact_pool_and_report_card():
    tb = {"snapshot": {"pe": 20, "market_cap_cr": 1000, "latest": {}},
          "trajectory": {"cagr_pct": {"5y": {"revenue": 12.2, "pat": 8.7}}, "quarters": [], "quarters_with_yoy_revenue_growth": "8 of 8"},
          "balance_sheet": {"debt_to_equity": 0.1, "borrowings": 50}, "cash_quality": {"three_year_cfo_to_pat": 1.1}}
    led = {"kept_of_measurable": "1 of 2", "counts": {"Kept": 1, "Missed": 1, "Partly": 0, "Quietly dropped": 1, "Too early": 0, "Not measurable": 0},
           "promises": [{"verdict": "Quietly dropped", "metric": "ebit_margin", "horizon": "FY26", "target": "8%", "actual": None,
                         "said": {"quote": "q", "page": 2, "source_url": "u", "call_date": "2025-07-31"}}]}
    dod = [{"call": "2026-10-31", "summary": "questions dodged: 1 of 4", "counts": {"dodged": 1},
            "judged": [{"label": "dodged", "reason": "no number", "question_quote": "a", "question_page": 3,
                        "answer_quote": "b", "answer_page": 4}] + [{"label": "answered"}] * 3}]
    facts = narrative.fact_pool(tb, led, dod)
    assert facts[0]["id"] == "F1" and any("dodged: 1 of 4" in f["text"] for f in facts)
    rc = engine.report_card(led, dod)
    assert rc["promises_kept"] == "1 of 2" and rc["questions_dodged"] == "1 of 4" and rc["topics_dropped"] == ["ebit margin FY26 (8%)"]


def test_dodge_needs_evidence():
    from finn.pull import dodged

    q = "How much will margins expand next year?"
    assert dodged.confirm_dodge(q, "We will not give a number on that.", "We will not give a number on that")[0] == "dodged"
    assert dodged.confirm_dodge(q, "Demand is good and we are investing.", "Demand is good and we are investing")[0] == "dodged"
    assert dodged.confirm_dodge(q, "Margins should be 21% next year.", "Margins should be 21%")[0] == "partly"
    assert dodged.confirm_dodge("Where is the second programme?", "Sorry, what is the second program you talked about?",
                                "Sorry, what is the second program you talked about?")[0] == "partly"
    assert dodged.confirm_dodge("Any update on the plant?", "I do not have any specific comments on it right now.",
                                "I do not have any specific comments on it right now")[0] == "dodged"


def test_ask_answers_only_from_evidence(fake_router):
    from finn.pull import ask

    research = {"name": "Demo Ltd", "ticker": "DEMO", "sections": {
        "facts": [{"id": "F1", "text": "Debt/equity 1.24 (borrowings Rs 140,300 cr)", "source": "balance sheet"}],
        "promise_ledger": {"promises": [{"verdict": "Missed", "metric": "revenue_growth", "horizon": "FY26", "target": "15%",
                                         "scope": "company", "reason": "target 15%, actual 11.8%",
                                         "said": {"call_date": "2026-01-31", "quote": "revenue growth guidance of 15%",
                                                  "source_url": "u", "page": 8}}]}}}
    ev = ask.evidence(research)
    assert [e["id"] for e in ev] == ["E1", "E2"] and ev[1]["page"] == 8
    fake_router({"covered": True, "answer": "No: target 15%, actual 11.8%.", "cites": ["E2"]})
    a = ask.ask(research, "Did they meet FY26 revenue guidance?")
    assert a["status"] == "answered" and a["citations"][0]["page"] == 8
    fake_router({"covered": True, "answer": "Revenue grew 22% in FY26.", "cites": ["E2"]})
    assert ask.ask(research, "How fast did revenue grow?")["status"] == "refused"      # invented number
    fake_router({"covered": False, "answer": "No CEO information in the evidence.", "cites": []})
    assert ask.ask(research, "Who is the CEO?")["status"] == "not_covered"


def test_table_maths():
    assert tables.cagr(100, 161.05, 5) == 10.0
    assert tables.cagr(-1, 100, 5) is None


def test_segment_page_finder():
    seg = "Segment Information (Consolidated)\nSegment Revenue\n" + " ".join(f"{i},{i:03d}.50" for i in range(30))
    pages = ["Directors report", seg, "Notes to accounts 1.0"]
    assert business.find_segment_pages(pages) == [1]


def test_revenue_jump_flags_a_merger_sized_year_only():
    from finn.pull.narrative import revenue_jump
    rows = lambda revs: [{"year_end": f"20{20 + i}-03-31", "revenue": v} for i, v in enumerate(revs)]
    # HDFC Bank shape: ~6-25% a year, then +66% in the merger year.
    assert revenue_jump(rows([120000, 128552, 135936, 170754, 283649, 336367, 348615])) == ("2024-03-31", 66.1)
    # Steady 20% growth is not a jump.
    assert revenue_jump(rows([100, 120, 144, 173, 207, 249])) is None


def test_merger_flag_needs_per_share_dilution():
    from finn.pull.narrative import fact_pool
    annual = [{"year_end": f"20{20 + i}-03-31", "revenue": v} for i, v in
              enumerate([120000, 128552, 135936, 170754, 283649, 336367, 348615])]
    tb = lambda eps: {"snapshot": {}, "balance_sheet": {}, "cash_quality": {},
                      "trajectory": {"annual": annual, "cagr_pct": {"3y": {"revenue": 26.9, "pat": 19.7, "eps": eps}}}}
    merged = " ".join(f["text"] for f in fact_pool(tb(6.2), None, None))
    organic = " ".join(f["text"] for f in fact_pool(tb(25.0), None, None))
    assert "not like-for-like" in merged and "not like-for-like" not in organic


def test_finns_take_is_built_from_facts():
    from finn.pull.narrative import finns_take
    q = [{"quarter_end": f"q{i}", "revenue": 100 + i, "pat": 10} for i in range(4)] + [{"quarter_end": "q4", "revenue": 110, "pat": 9}]
    S = {"trajectory": {"cagr_pct": {"3y": {"revenue": 29.0, "eps": 25.0}}, "quarters": q, "annual": []},
         "promise_ledger": {"counts": {"Kept": 3, "Missed": 3}, "promises": [{}] * 6},
         "report_card": {"questions_dodged": "2 of 20"}, "balance_sheet": {}, "cash_quality": {}}
    t = finns_take(S)["text"]
    assert t.startswith("Kept 3 of 6 promises") and "growth slowing 29% → 10%" in t
    assert "margins under pressure" in t and "dodged 2 of 20" in t


def test_queue_position_counts_jobs_ahead():
    from finn.pull import engine
    engine._jobs.clear()
    engine._jobs.update({
        "a": {"id": "a", "ticker": "A", "status": "running", "stage": "reading transcripts", "created": 1.0},
        "b": {"id": "b", "ticker": "B", "status": "queued", "stage": None, "created": 2.0},
        "c": {"id": "c", "ticker": "C", "status": "queued", "stage": None, "created": 3.0},
    })
    assert engine.status("c")["ahead"] == 2 and engine.status("b")["ahead"] == 1 and engine.status("a")["ahead"] == 0
    engine._jobs.clear()



def test_bank_numbers_from_statement_tables():
    from finn.pull.tables import bank
    f = {"lender": True,
         "quarterly": {"2025-09-30": {"revenue": 87000.0, "interest": 47000.0},
                       "2026-09-30": {"revenue": 95132.0, "interest": 50667.0, "gross_npa_pct": None}},
         "balance_sheet": {"2025-09-30": {"deposits": 3100000.0}, "2026-09-30": {"deposits": 3324146.0, "total_assets": 5165842.0}}}
    b = bank(f)
    assert b["nii"] == 44465.0 and b["nii_yoy_pct"] == 11.2 and b["nim_approx_pct"] == 3.44
    assert b["deposit_growth_pct"] == 7.2 and "CASA ratio" in b["missing"]
    assert bank({"lender": False}) is None
