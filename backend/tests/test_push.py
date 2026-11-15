"""Push engine: every deterministic part, offline, against real filings and recorded model answers."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

import pytest

from finn import llm
from finn.filings import IST
from finn.push import (alerts, classify, digest, evaluate, materiality, people, portfolio, results_card,
                       summarize, taxonomy)
from conftest import FIX


def _fx(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ portfolio + classifier accuracy
def test_portfolio_loads_and_weights_sum_to_one():
    p = portfolio.load()
    assert len(p.symbols) == 18 and abs(sum(p.weights.values()) - 1) < 1e-9
    assert set(p.preferences) == set(taxonomy.CATEGORIES)


def test_rules_accuracy_on_hand_labelled_portfolio_filings():
    d = _fx("labelled_filings.json")
    r = evaluate.evaluate(d["items"], use_llm=False, p=portfolio.load(), mcaps=d["market_caps_cr"])
    assert r["n"] == 90
    assert r["category_accuracy"] >= 0.95, r["errors"]
    assert r["treatment_accuracy"] >= 0.95, r["errors"]
    assert r["treatment_confusion"].get("hero -> collapsed", 0) == 0          # never bury a hero


def test_rules_accuracy_on_heldout_filings():
    r = evaluate.evaluate(_fx("heldout_filings.json")["items"], use_llm=False)
    assert r["category_accuracy"] >= 0.8, r["errors"]


@pytest.mark.parametrize("subject,detail,cat,sub", [
    ("Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation", "", "investor_meetings", "meet"),
    ("Analysts/Institutional Investor Meet/Con. Call Updates", "schedules a conference call with J.P. Morgan",
     "investor_meetings", "meet"),
    ("Announcement under Regulation 30 (LODR)-Earnings Call Transcript", "", "earnings_call", "transcript"),
    ("Outcome of Board Meeting", "has submitted to the Exchange, the financial results for the period ended", "results", "financials"),
    ("Announcement under Regulation 30 (LODR)-Newspaper Publication", "financial results", "results", "newspaper_ad"),
    ("Reference To The Financial Results Issued By Suzuki Motor Corporation", "", "press_release", "related_company_results"),
    ("Change in Management", "Appointment of Mr X as Chief Financial Officer", "management_change", "top"),
    ("Change in Management", "Appointment of Mr X as Non-Executive Independent Director", "management_change", "board"),
    ("Outcome of Board Meeting", "Appointment of M/S ABC LLP as Statutory Auditor", "management_change", "auditor"),
    ("Credit Rating", "outlook revised to Positive from Stable", "credit_rating", "upgrade"),
    ("Credit Rating", "rating reaffirmed", "credit_rating", "reaffirm"),
    ("Corporate Insolvency Resolution Process (CIRP)-Updates", "", "litigation", "insolvency"),
    ("Allotment", "Allotment of non-convertible debentures", "fund_raise", "debt"),
    ("Shareholders meeting", "Scrutinizer's Report of the NCLT (\"NCLT\") Convened Meeting", "M&A", "scheme_vote"),
    ("Allotment of ESOP / ESPS", "", "unclassified", "esop"),
])
def test_rule_cases(subject, detail, cat, sub):
    c, _ = classify.rule_classify({"subject": subject, "detail": detail})
    assert (c.category, c.subtype) == (cat, sub)


def test_unknown_filing_asks_for_llm_and_stays_unclassified_offline():
    c, needs = classify.rule_classify({"subject": "Please refer enclosed herewith", "detail": ""})
    assert needs and c.category == "unclassified"
    assert classify.classify({"subject": "Please refer enclosed herewith"}, use_llm=True).category == "unclassified"


def test_attachment_name_only_when_readable():
    assert classify.attachment_name("https://x/corporate/ORIANA_1411_FinalResult.pdf") == "ORIANA 1411 FinalResult"
    assert classify.attachment_name("https://x/AttachLive/2fbcc369-8f64-46ad-bdad-4fcf33472322.pdf") == ""


# ------------------------------------------------------------------ materiality
def _c(cat, sub, base, routine=False):
    return taxonomy.Classification(cat, sub, base, 0.9, "rule", routine)


def test_score_parts_explain_every_factor():
    f = {"subject": "Preferential allotment", "detail": "raising Rs 5,000 crore"}
    s = materiality.score(f, _c("fund_raise", "equity", 0.72), weight=0.1, mcap_cr=50_000,
                          prefs={"fund_raise": 1.0}, reaction={"date": "2026-11-12", "ret_pct": 4.0, "z": 3.0, "vol_x": 2.5})
    whys = " | ".join(p["why"] for p in s.parts)
    assert "fund raise / equity" in whys and "10.0% of market cap" in whys and "holding weight" in whys and "moved unusually" in whys
    expected = min(1.0, 0.72 * 0.8 * 1.5 * 1.1 + 0.1)     # allotment x size x weight + reaction
    assert s.value == round(expected, 3) and s.treatment == "hero"


def test_planned_vs_abrupt_management_change():
    c = _c("management_change", "top", 0.75)
    planned = materiality.score({"detail": "re-appointment of the CFO"}, c)
    abrupt = materiality.score({"detail": "CFO resigned with immediate effect for personal reasons"}, c)
    assert planned.value < 0.6 <= abrupt.value


def test_routine_always_collapsed_and_thresholds():
    s = materiality.score({}, _c("results", "newspaper_ad", 0.95, routine=True))
    assert s.treatment == "collapsed"
    assert materiality.treatment_for(0.6, False) == "hero"
    assert materiality.treatment_for(0.3, False) == "one_liner"
    assert materiality.treatment_for(0.299, False) == "collapsed"


def test_amount_extraction():
    assert materiality.extract_amount_cr("raising ₹4,264.6 crore in QIP")[0] == pytest.approx(4264.6)
    assert materiality.extract_amount_cr("INR 6 billion of CPs")[0] == pytest.approx(600)
    assert materiality.extract_amount_cr("Rs 50 lakh")[0] == pytest.approx(0.5)
    assert materiality.extract_amount_cr("US$ 500 million notes")[0] == pytest.approx(500 * 0.1 * materiality.USD_TO_INR)
    assert materiality.extract_amount_cr("at ₹1,010 each") is None


# ------------------------------------------------------------------ results card (recorded model answers)
def test_itc_extraction_passes_every_check_and_matches_screener():
    d = _fx("results_extractions.json")
    checks = results_card.check(d["itc"], d["itc_screener_quarter"], "consolidated")
    assert all(c["ok"] for c in checks), checks
    names = {c["name"] for c in checks}
    assert {"revenue matches screener", "pat matches screener", "PBT - tax = PAT"} <= names
    m = results_card.compute(d["itc"])
    assert m["revenue"]["note"] == "net of excise duty"
    L = d["itc"]["lines"]
    net = L["revenue_from_operations"][0] - L["excise_duty"][0]
    assert m["revenue"]["value"] == round(net, 2)
    assert m["revenue"]["yoy_pct"] == round((net / (L["revenue_from_operations"][2] - L["excise_duty"][2]) - 1) * 100, 1)


def test_card_summary_is_written_from_the_verified_numbers():
    d = _fx("results_extractions.json")
    card = {"status": "verified", "period_type": "quarter", "basis": "consolidated",
            "period_ends": d["itc"]["period_ends"], "metrics": results_card.compute(d["itc"])}
    s = results_card.summary(card, "ITC")
    pat = card["metrics"]["pat"]
    assert s["headline"] == f"ITC results: PAT Rs {pat['value']:,.0f} cr, {pat['yoy_pct']:+.1f}% YoY"
    assert len(s["headline"]) <= 70 and len(s["one_liner"]) <= 140 and "30 Sep 2026" in s["one_liner"]
    assert results_card.summary({**card, "status": "not_verified"}, "ITC") is None


def test_dividend_template_does_not_hijack_a_results_filing():
    src = "Financial results for the quarter. The Board declared an Interim Dividend of Rs. 3.05 per equity share."
    assert summarize.template({}, src, category="results") is None
    assert summarize.template({}, src, category="dividend")["headline"] == "Interim dividend of Rs 3.05 per share"


def test_gross_revenue_would_fail_the_screener_check():
    d = _fx("results_extractions.json")
    gross = json.loads(json.dumps(d["itc"]))
    del gross["lines"]["excise_duty"]
    bad = [c for c in results_card.check(gross, d["itc_screener_quarter"], "consolidated") if not c["ok"]]
    assert [c["name"] for c in bad] == ["revenue matches screener"]


def test_half_year_and_reordered_columns():
    d = _fx("results_extractions.json")
    assert results_card.period_type(d["half_year"]) == "half_year"
    fixed = results_card.reorder(d["out_of_order"])
    assert fixed["reordered_columns"] and results_card.period_type(fixed) == "half_year"
    assert fixed["period_ends"][0] > fixed["period_ends"][1] > fixed["period_ends"][2]
    assert all(c["ok"] for c in results_card.check(fixed, None, None))


def test_pbt_tax_pat_mismatch_is_caught():
    ex = {"basis": "standalone", "unit": "crore", "is_bank_or_nbfc_format": False,
          "period_ends": ["2026-09-30", "2026-06-30", "2025-09-30"],
          "lines": {"revenue_from_operations": [100, 90, 80], "profit_before_tax": [20, 18, 16],
                    "tax_expense": [5, 4, 4], "profit_after_tax": [30, 14, 12]}}
    bad = {c["name"] for c in results_card.check(ex, None, None) if not c["ok"]}
    assert bad == {"PBT - tax = PAT"}


def test_ebitda_and_bank_metrics_computed_in_python():
    ex = {"unit": "lakh", "is_bank_or_nbfc_format": False, "lines": {
        "revenue_from_operations": [1000, 900, 800], "other_income": [10, 10, 10], "finance_costs": [20, 20, 20],
        "depreciation": [30, 30, 30], "profit_before_tax": [200, 180, 150], "profit_after_tax": [150, 135, 110]}}
    m = results_card.compute(ex)
    assert m["ebitda"]["value"] == round((200 + 20 + 30 - 10) * 0.01, 2)
    assert m["ebitda_margin_pct"]["value"] == 24.0
    bank = {"unit": "crore", "is_bank_or_nbfc_format": True, "lines": {
        "interest_earned": [100, 95, 90], "interest_expended": [60, 58, 55], "provisions": [5, 6, 7],
        "profit_before_tax": [20, 18, 16], "profit_after_tax": [15, 14, 12], "gross_npa_pct": [1.2, 1.3, 1.4]}}
    mb = results_card.compute(bank)
    assert mb["net_interest_income"]["value"] == 40 and "revenue" not in mb and mb["gross_npa_pct"]["value"] == 1.2


def test_result_page_finder():
    table = ("Statement of Unaudited Consolidated Financial Results for the Quarter ended 30.09.2026\n"
             "Revenue from operations 1,234.56 1,111.22 999.10\nProfit before tax 123.45 111.11 99.99\n"
             + " ".join(f"{i}.{i:02d}" for i in range(40)))
    pages = ["Cover letter to the exchange", table, "Notes: reviewed by the audit committee"]
    idx, basis = results_card.find_result_pages(pages)
    assert idx == [1] and basis == "consolidated"


# ------------------------------------------------------------------ people card
def test_people_quotes_must_be_in_the_filing():
    pages = ["Outcome of board meeting.", "Mr. Rakesh Sony is appointed as Additional Director. He has over 25 years of "
             "experience in investment banking and private equity."]
    raw = [{"name": "Mr. Rakesh Sony", "role": "Additional Director", "change": "appointment",
            "effective_date": "2026-11-13", "reason": "", "background": [
                {"quote": "He has over 25 years of experience in investment banking and private equity.", "page": 1},
                {"quote": "He was CEO of a Fortune 500 company.", "page": 2}]},
           {"name": "Someone Invented", "role": "CFO", "change": "resignation", "effective_date": "", "reason": "",
            "background": []}]
    kept, dropped = people.verify_people(raw, pages)
    assert [p["name"] for p in kept] == ["Rakesh Sony"]
    assert kept[0]["background"] == [{"text": raw[0]["background"][0]["quote"], "page": 2, "source": "filing"}]
    assert dropped == 2
    assert people.headline({"people": kept}) == "Rakesh Sony appointed Additional Director, effective 2026-11-13"


# ------------------------------------------------------------------ summaries
SRC = "Subject: Order win\nL&T has won an order worth Rs 2,500 crore from Noida Metro on November 9, 2026."


def test_summary_checks_numbers_adjectives_actions_and_length():
    good = {"headline": "L&T wins Rs 2,500 crore Noida Metro order", "one_liner": "L&T won a Rs 2,500 crore order from Noida Metro on November 9, 2026."}
    assert summarize.validate(good, SRC) == []
    assert any("not in the filing" in p for p in summarize.validate({**good, "one_liner": "Order worth Rs 3,000 crore."}, SRC))
    assert any("adjectives" in p for p in summarize.validate({**good, "headline": "L&T wins major order on Nov 9, 2026"}, SRC))
    assert summarize.unsupported_adjectives("Major order worth Rs 2,500 crore") == []
    assert any("actions" in p for p in summarize.validate({**good, "headline": "L&T upgraded"}, SRC))
    assert any("length" in p for p in summarize.validate({**good, "headline": "x" * 71}, SRC))


def test_repair_only_deletes():
    fixed = summarize.repair({"headline": "L&T bags significant order from Noida Metro",
                              "one_liner": "L&T won a Rs 2,500 crore order from Noida Metro on November 9, 2026."}, SRC + " bags")
    assert fixed["headline"] == "L&T bags order from Noida Metro"


def test_templates_for_ratings_and_dividends():
    rating = ("ICRA has upgraded ratings of Suzlon Energy Limited as under: Total bank loan facilities rated Rs.2635 "
              "Crores Long term rating ICRA A+ / Positive (reaffirmed; outlooked revised to 'Positive' from 'Stable')")
    t = summarize.template({}, rating)
    assert t["headline"] == "ICRA A+ reaffirmed; outlook Stable to Positive"      # the rating line wins over the cover words
    div = "The Board recommended a Final Dividend of Rs. 0.75 per equity share. Record date is November 27, 2026."
    assert summarize.template({}, div)["one_liner"] == "Final dividend of Rs 0.75 per share; record date November 27, 2026"


def test_clean_subject():
    assert summarize.clean_subject("Announcement under Regulation 30 (LODR)-Credit Rating") == "Credit Rating"


# ------------------------------------------------------------------ alerts
def _bars(n, f_ret, vol=lambda i: 1000):
    out, px, mkt = [], 100.0, 100.0
    stock, market = [], []
    d0 = datetime(2026, 1, 1)
    for i in range(n):
        m = 0.01 * math.sin(i * 1.7)
        mkt *= 1 + m
        px *= 1 + f_ret(i, m)
        day = (d0 + timedelta(days=i)).date().isoformat()
        stock.append({"date": day, "close": px, "volume": vol(i)})
        market.append({"date": day, "close": mkt, "volume": 1})
    return stock, market


def test_series_beta_and_unusual_day():
    noise = lambda i: 0.004 * math.cos(i * 2.3)                                # noqa: E731
    stock, market = _bars(200, lambda i, m: 1.5 * m + noise(i) + (0.06 if i == 199 else 0),
                          vol=lambda i: 3000 if i == 199 else 1000)
    rows = alerts.compute_series(stock, market)
    last = rows[-1]
    assert 1.4 <= last["beta"] <= 1.6
    assert last["z"] > 5 and last["vol_x"] == 3.0
    assert alerts.PRESETS["unusual_move"].fires(last) and alerts.PRESETS["volume_spike"].fires(last)
    assert not alerts.PRESETS["unusual_move"].fires(rows[-2])
    assert "sigma above its normal day" in alerts.describe("ABC", last)


def test_backtest_counts_fires():
    stock, market = _bars(200, lambda i, m: m + (0.08 if i in (150, 170, 190) else 0.002 * math.cos(i)))
    series = {"ABC": alerts.compute_series(stock, market), "XYZ": alerts.compute_series(*_bars(200, lambda i, m: m))}
    bt = alerts.backtest("big_day", series, days=90)
    assert bt["fires_total"] == 3 and list(bt["per_symbol"]) == ["ABC"] and bt["quiet_symbols"] == ["XYZ"]
    with pytest.raises(ValueError):
        alerts.rule_from({"min_z": 2})


def test_filings_before_a_move_are_linked_by_timing_only():
    a = {"symbol": "ABC", "date": "2026-11-12"}
    fl = {"ABC": [{"ts": "2026-11-11T18:00:00+05:30", "subject": "Results", "treatment": "hero"},
                  {"ts": "2026-11-12T17:00:00+05:30", "subject": "After the close", "treatment": "hero"},
                  {"ts": "2026-11-01T10:00:00+05:30", "subject": "Too old", "treatment": "hero"}]}
    assert [x["title"] for x in alerts.link_filings(a, fl)] == ["Results"]


# ------------------------------------------------------------------ digest helpers
def test_reaction_uses_next_day_after_the_close():
    rows = [{"date": "2026-11-11", "ret_pct": 1, "z": 0.5, "vol_x": 1}, {"date": "2026-11-12", "ret_pct": 4, "z": 3, "vol_x": 2}]
    assert digest.reaction_for({"ts": "2026-11-11T10:00:00+05:30"}, rows)["date"] == "2026-11-11"
    assert digest.reaction_for({"ts": "2026-11-11T17:00:00+05:30"}, rows)["date"] == "2026-11-12"


def test_cluster_keeps_most_material_as_lead():
    items = [{"uid": "a", "symbol": "X", "category": "fund_raise", "score": 0.5, "ts": "1", "subject": "Allotment", "url": None, "treatment": "one_liner"},
             {"uid": "b", "symbol": "X", "category": "fund_raise", "score": 0.8, "ts": "2", "subject": "QIP opens", "url": None, "treatment": "hero"},
             {"uid": "c", "symbol": "X", "category": "unclassified", "score": 0.0, "ts": "3", "subject": "ESOP", "url": None, "treatment": "collapsed"}]
    ev = digest.cluster(items)
    lead = next(e for e in ev if e["category"] == "fund_raise")
    assert lead["subject"] == "QIP opens" and [r["title"] for r in lead["related"]] == ["Allotment"]
    assert len(ev) == 2


def test_results_candidates_try_other_exchange_filings(offline, monkeypatch):
    from finn.symbols import Instrument

    monkeypatch.setattr(digest.symbols, "resolve", lambda t: Instrument("ABC", "500001", "ABC Ltd"))
    now = datetime.now(IST).isoformat(timespec="seconds")
    offline.upsert_filings([{"uid": "BSE:r.pdf", "exchange": "BSE", "bse_code": "500001", "ts": now,
                             "subject": "Outcome of Board Meeting - Financial Results", "url": "https://www.bseindia.com/rss.pdf",
                             "source": "bse_rss"},
                            {"uid": "BSE:n.pdf", "exchange": "BSE", "bse_code": "500001", "ts": now,
                             "subject": "Newspaper publication of financial results", "url": "https://www.bseindia.com/ad.pdf",
                             "source": "bse_rss"}])
    e = {"symbol": "ABC", "url": "https://www.bseindia.com/press.pdf",
         "related": [{"url": "https://www.bseindia.com/press.pdf"}, {"url": "https://www.bseindia.com/outcome.pdf"}]}
    items = [{"symbol": "ABC", "category": "results", "subtype": "financials", "url": "https://www.bseindia.com/fin.pdf"}]
    assert digest.results_candidates(e, items) == ["https://www.bseindia.com/press.pdf", "https://www.bseindia.com/outcome.pdf",
                                                   "https://www.bseindia.com/fin.pdf"]
    digest.MAX_RESULT_TRIES = 5
    try:
        assert "https://www.bseindia.com/rss.pdf" in digest.results_candidates(e, items)
        assert "https://www.bseindia.com/ad.pdf" not in digest.results_candidates(e, items)
    finally:
        digest.MAX_RESULT_TRIES = 3


def test_windows(offline):
    now = datetime(2026, 11, 14, 9, 0, tzinfo=IST)
    assert digest.resolve_window("3d", now)[0] == now - timedelta(days=3)
    s, e, label = digest.resolve_window("since_last_look", now)
    assert label.startswith("last 24 hours") and s == now - timedelta(hours=24)
    digest._meta_set("last_look", "2026-11-13T20:00:00+05:30")
    assert digest.resolve_window("since_last_look", now)[2] == "since last look"
    with pytest.raises(ValueError):
        digest.resolve_window("2w", now)


# ------------------------------------------------------------------ LLM router (no network: fake client)
class _Resp:
    def __init__(self, text):
        self.text = text

        class U:
            prompt_token_count, candidates_token_count, thoughts_token_count = 100, 10, 0
        self.usage_metadata = U()


class _FakeModels:
    def __init__(self, behaviour):
        self.behaviour, self.calls = behaviour, []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        out = self.behaviour(model)
        if isinstance(out, Exception):
            raise out
        return _Resp(out)


class _FakeClient:
    def __init__(self, behaviour):
        self.models = _FakeModels(behaviour)


@pytest.fixture
def no_pacing(monkeypatch):
    monkeypatch.setattr(llm, "MIN_GAP_SECONDS", {"lite": 0, "flash": 0})
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def test_router_caches_by_content_hash(no_pacing):
    client = _FakeClient(lambda m: '{"category": "results"}')
    r = llm.Router(client=client)
    a = r.complete("t", "same prompt", schema={"type": "object"})
    b = r.complete("t", "same prompt", schema={"type": "object"})
    assert a.data == b.data == {"category": "results"} and not a.cached and b.cached
    assert len(client.models.calls) == 1
    r.complete("t", "different prompt", schema={"type": "object"})
    assert len(client.models.calls) == 2


def test_router_falls_back_and_labels_it(no_pacing):
    first = llm.TIERS["lite"][0]
    client = _FakeClient(lambda m: ValueError("400 bad model") if m == first else "ok")
    res = llm.Router(client=client).complete("t", "p")
    assert res.text == "ok" and res.fallback and res.model == llm.TIERS["lite"][1] and res.notes


def test_router_retries_transient_errors(no_pacing):
    seen = []

    def behaviour(m):
        seen.append(m)
        return RuntimeError("503 UNAVAILABLE") if len(seen) < 3 else "fine"
    res = llm.Router(client=_FakeClient(behaviour)).complete("t", "p")
    assert res.text == "fine" and seen[:3] == [llm.TIERS["lite"][0]] * 3


def test_router_offline_returns_none_and_usage_counts(no_pacing, monkeypatch):
    monkeypatch.setenv("FINN_OFFLINE", "1")          # never reach the live model from a test
    assert llm.Router(client=None).complete("t", "never cached") is None and not llm.Router(client=None).available
    llm.Router(client=_FakeClient(lambda m: "x")).complete("t", "count me")
    u = llm.usage()
    assert u["cost_usd"] == 0.0 and sum(v["api_calls"] for v in u["models"].values()) >= 1
