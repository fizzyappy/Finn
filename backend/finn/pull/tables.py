"""Research sections built from the statement tables alone. No LLM, every number
computed here, every number traceable to a table cell (screener.in, Rs crore).

financial snapshot, multi-year trajectory, balance sheet, cash quality.
Lenders (banks / NBFCs) get their own schema: no EBITDA, no working-capital cycle.
"""
from __future__ import annotations

from .. import fundamentals


def _years(table: dict) -> list[str]:
    return [p for p in table if p[:4].isdigit()]


def _get(table: dict, period: str, key: str):
    return (table.get(period) or {}).get(key)


def cagr(first: float | None, last: float | None, years: int) -> float | None:
    if not first or not last or first <= 0 or last <= 0 or years <= 0:
        return None
    return round(((last / first) ** (1 / years) - 1) * 100, 1)


def pct(a, b):
    return fundamentals.growth_pct(a, b)[0]


def snapshot(f: dict) -> dict:
    q = f["quarterly"]
    qs = _years(q)
    a = f["annual"]
    ttm = a.get("TTM") or {}
    tr = f["top_ratios"]

    def ratio(name):
        v = (tr.get(name) or {}).get("values") or []
        return v[0] if v else None
    latest = qs[-1] if qs else None
    out = {
        "latest_quarter": latest, "basis": f["basis"], "units": "Rs crore", "lender": f["lender"],
        "market_cap_cr": ratio("Market Cap"), "price": ratio("Current Price"), "pe": ratio("Stock P/E"),
        "book_value": ratio("Book Value"), "roe_pct": ratio("ROE"), "roce_pct": ratio("ROCE"),
        "dividend_yield_pct": ratio("Dividend Yield"),
        "ttm": {k: ttm.get(k) for k in ("revenue", "ebitda", "pat", "eps") if ttm.get(k) is not None},
        "source": f.get("source_url"),
    }
    if out["market_cap_cr"] and ttm.get("revenue"):
        out["price_to_sales"] = round(out["market_cap_cr"] / ttm["revenue"], 2)
    if latest:
        cur = q[latest]
        out["latest"] = {k: cur.get(k) for k in ("revenue", "ebitda", "ebitda_margin_pct", "pat", "eps",
                                                  "financing_profit", "gross_npa_pct", "net_npa_pct") if cur.get(k) is not None}
    return out


def trajectory(f: dict) -> dict:
    a, q = f["annual"], f["quarterly"]
    ys = _years(a)
    rows = []
    for y in ys[-10:]:
        r = a[y]
        rev, eb, pat = r.get("revenue"), r.get("ebitda"), r.get("pat")
        rows.append({"year_end": y, "revenue": rev, "ebitda": eb, "pat": pat, "eps": r.get("eps"),
                     "ebitda_margin_pct": round(eb / rev * 100, 1) if rev and eb is not None else None,
                     "pat_margin_pct": round(pat / rev * 100, 1) if rev and pat is not None else None})
    out = {"annual": rows, "cagr_pct": {}}
    for n in (3, 5, 10):
        if len(ys) > n:
            a0, a1 = a[ys[-1 - n]], a[ys[-1]]
            out["cagr_pct"][f"{n}y"] = {k: cagr(a0.get(k), a1.get(k), n) for k in ("revenue", "pat", "eps")}
    qs = _years(q)[-8:]
    out["quarters"] = [{"quarter_end": p, **{k: q[p].get(k) for k in ("revenue", "ebitda", "pat", "ebitda_margin_pct")}}
                       for p in qs]
    # Consistency: how many of the last 8 quarters grew revenue year on year?
    grew = 0
    allq = _years(q)
    for p in qs:
        i = allq.index(p)
        if i >= 4 and q[p].get("revenue") and q[allq[i - 4]].get("revenue"):
            grew += q[p]["revenue"] > q[allq[i - 4]]["revenue"]
    out["quarters_with_yoy_revenue_growth"] = f"{grew} of {sum(1 for p in qs if allq.index(p) >= 4)}"
    return out


def balance_sheet(f: dict) -> dict:
    bs, ratios = f["balance_sheet"], f["ratios"]
    ys = _years(bs)
    if not ys:
        return {"available": False}
    last = bs[ys[-1]]
    equity = (last.get("equity_capital") or 0) + (last.get("reserves") or 0)
    debt = last.get("borrowings")
    out = {"as_of": ys[-1], "net_worth": round(equity, 1), "borrowings": debt,
           "total_assets": last.get("total_assets"), "lender": f["lender"]}
    if f["lender"]:
        out["deposits"] = last.get("deposits")
        prev = bs[ys[-2]] if len(ys) > 1 else {}
        if last.get("deposits") and prev.get("deposits"):
            out["deposit_growth_pct"] = pct(last["deposits"], prev["deposits"])
        out["equity_to_assets_pct"] = round(equity / last["total_assets"] * 100, 1) if last.get("total_assets") else None
        out["note"] = "Lender: debt/equity and working-capital cycle do not apply."
        return out
    out["debt_to_equity"] = round(debt / equity, 2) if debt is not None and equity else None
    out["debt_trend"] = [{"year_end": y, "borrowings": bs[y].get("borrowings")} for y in ys[-5:]]
    ry = _years(ratios)
    if ry:
        r = ratios[ry[-1]]
        out["working_capital"] = {"year_end": ry[-1], **{k: r.get(k) for k in
                                  ("debtor_days", "inventory_days", "payable_days", "ccc_days", "wc_days") if r.get(k) is not None}}
        out["roce_trend_pct"] = [{"year_end": y, "roce_pct": ratios[y].get("roce_pct")} for y in ry[-5:]]
    return out


def cash_quality(f: dict) -> dict:
    cf, a = f["cash_flow"], f["annual"]
    ys = [y for y in _years(cf) if y in a]
    if not ys:
        return {"available": False}
    rows = []
    for y in ys[-6:]:
        cfo, pat = cf[y].get("cfo"), a[y].get("pat")
        fcf = cf[y].get("fcf")
        rows.append({"year_end": y, "cfo": cfo, "pat": pat, "fcf": fcf,
                     "cfo_to_pat": round(cfo / pat, 2) if cfo is not None and pat else None,
                     "cfo_to_ebitda_pct": cf[y].get("cfo_to_ebitda_pct")})
    last3 = ys[-3:]
    sum_cfo = sum(cf[y].get("cfo") or 0 for y in last3)
    sum_pat = sum(a[y].get("pat") or 0 for y in last3)
    out = {"years": rows, "three_year_cfo_to_pat": round(sum_cfo / sum_pat, 2) if sum_pat else None,
           "lender": f["lender"]}
    if f["lender"]:
        out["note"] = "Lender: operating cash flow mostly reflects loan and deposit movements; CFO/PAT is not a quality signal."
    else:
        r = out["three_year_cfo_to_pat"]
        out["reading"] = None if r is None else (
            f"Over the last 3 years, operating cash flow was {r:.2f}x reported profit"
            + (" (cash backs the profits)" if r >= 0.9 else " (profits are not fully turning into cash)"))
    return out


def build(ticker: str) -> dict:
    fd = fundamentals.get_fundamentals(ticker)
    f = fd.data
    return {"instrument": f["instrument"], "name": f["name"], "data_as_of": fd.as_of, "stale": fd.stale,
            "snapshot": snapshot(f), "trajectory": trajectory(f), "balance_sheet": balance_sheet(f),
            "cash_quality": cash_quality(f)}
