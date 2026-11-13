"""Live end-to-end check against the real sources. Writes backend/validation_report.md.

Nothing here is mocked: every number in the report was fetched during the run.
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from pathlib import Path

from . import documents, filings, fundamentals, prices, symbols

DEFAULT = ["RELIANCE", "INFY", "HDFCBANK", "SUZLON", "RATEGAIN"]
REPORT = Path(__file__).resolve().parents[1] / "validation_report.md"


def _step(fn):
    t = time.time()
    try:
        return {"ok": True, "value": fn(), "secs": round(time.time() - t, 1)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}", "secs": round(time.time() - t, 1),
                "trace": traceback.format_exc(limit=3)}


def _doc_check(url: str | None, trusted: set[str] = frozenset(), missing: str = "no link found") -> dict:
    if not url:
        return {"ok": False, "error": missing}
    def go():
        t = documents.get_text(url, trusted=trusted)
        # Round-trip the quote verifier on a real sentence from the document.
        sample = ""
        for p in t["pages"]:
            for line in p.splitlines():
                if len(line.split()) >= 8:
                    sample = line.strip()
                    break
            if sample:
                break
        return {"url": url, "pages": t["page_count"], "chars": t["text_chars"], "kb": t["bytes"] // 1024,
                "method": t["method"], "status": t["status"], "sample": sample[:160],
                "quote_check_page": documents.find_quote(t["pages"], sample) if sample else None}
    return _step(go)


def check_company(tk: str) -> dict:
    r: dict = {"ticker": tk}
    r["resolve"] = _step(lambda: symbols.resolve(tk).to_dict())
    if not r["resolve"]["ok"]:
        return r

    def px():
        f = prices.get_prices(tk, "1y")
        s = prices.summary(f.data)
        # Independent cross-check: screener's quoted current price vs our latest close.
        cp = fundamentals.get_fundamentals(tk).data["top_ratios"].get("Current Price", {}).get("values") or [None]
        diff = round((s["close"] / cp[0] - 1) * 100, 2) if cp[0] else None
        return {"meta": f.meta(), "summary": s, "first": f.data[0]["date"],
                "provisional_last": bool(f.data[-1].get("provisional")),
                "screener_price": cp[0], "diff_vs_screener_pct": diff}
    r["prices"] = _step(px)
    r["results"] = _step(lambda: fundamentals.headline_results(tk))

    def fund():
        d = fundamentals.get_fundamentals(tk).data
        docs = d["documents"]
        return {
            "basis": d["basis"], "lender": d["lender"],
            "quarters": len([p for p in d["quarterly"] if p[:4].isdigit()]),
            "years_pl": len([p for p in d["annual"] if p[:4].isdigit()]),
            "years_bs": len(d["balance_sheet"]), "years_cf": len(d["cash_flow"]), "years_ratios": len(d["ratios"]),
            "shareholding_q": len(d["shareholding"]),
            "annual_reports": len(docs["annual_reports"]),
            "concalls": len(docs["concalls"]),
            "transcripts": sum(1 for c in docs["concalls"] if c["transcript"]),
            "results_pdfs": len(d["quarter_pdfs"]),
            "latest_transcript": next((c["transcript"] for c in docs["concalls"] if c["transcript"]), None),
            "latest_transcript_period": next((c["period"] for c in docs["concalls"] if c["transcript"]), None),
            "pe": d["top_ratios"].get("Stock P/E", {}).get("text"),
            "mcap": d["top_ratios"].get("Market Cap", {}).get("text"),
        }
    r["fundamentals"] = _step(fund)
    r["filings"] = _step(lambda: filings.get_filings(tk, days=7))
    f = r["fundamentals"].get("value") or {}
    rd = _step(lambda: fundamentals.results_document(tk))
    r["results_doc"] = rd.get("value") if rd["ok"] else None
    trusted = _step(lambda: fundamentals.document_links(tk)).get("value") or set()
    r["results_pdf"] = _doc_check((r["results_doc"] or {}).get("url"), trusted,
                                  missing="no results filing or post-quarter presentation reachable "
                                          "(exchange APIs blocked; screener's results PDFs need a login)")
    lt = _step(lambda: fundamentals.latest_transcript(tk)).get("value") or {}
    r["transcript_doc"] = lt
    r["transcript_pdf"] = _doc_check(lt.get("url"), trusted)
    return r


def _fmt(n, d=0):
    if n is None:
        return "–"
    return f"{n:,.{d}f}"


def _pct(n):
    return "–" if n is None else f"{n:+.1f}%"


def render(run: dict) -> str:
    L = [f"# FINN data layer: live validation", "",
         f"Run: {run['started']} (IST, this PC's connection). Every number below was fetched live during this run.", ""]
    L += ["## Sources", "", "| Check | Result |", "|---|---|"]
    L.append(f"| RSS poll (BSE + NSE official feeds) | {run['rss']} |")
    n = run["nifty"]
    if n["ok"]:
        s = n["value"]["summary"]
        L.append(f"| Nifty 50 (^NSEI), {n['value']['meta']['source']} | close {_fmt(s['close'], 2)} on {s['date']} "
                 f"({_pct(s['change_pct'])}), 52w {_fmt(s['low_52w'])}–{_fmt(s['high_52w'])} |")
    else:
        L.append(f"| Nifty 50 | FAILED: {n['error']} |")
    L.append("")

    L += ["## Summary", "",
          "| Company | Last close | 1y bars | Latest quarter | Revenue (Rs cr) | YoY | PAT (Rs cr) | YoY | Filings 7d | Results PDF | Transcript |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in run["companies"]:
        if not c["resolve"]["ok"]:
            L.append(f"| {c['ticker']} | resolve FAILED: {c['resolve']['error']} |" + " |" * 9)
            continue
        px = c["prices"]
        close = f"{_fmt(px['value']['summary']['close'], 2)} ({px['value']['summary']['date']})" if px["ok"] else "FAILED"
        bars = px["value"]["summary"]["bars"] if px["ok"] else "–"
        res = c["results"]
        if res["ok"]:
            m = res["value"]["metrics"]
            rv, pt = m.get("revenue", {}), m.get("pat", {})
            q = res["value"]["quarter_end"]
            rev, rvy = _fmt(rv.get("value")), _pct(rv.get("yoy_pct")) if rv.get("yoy_pct") is not None else (rv.get("yoy_note") or "–")
            pat, pty = _fmt(pt.get("value")), _pct(pt.get("yoy_pct")) if pt.get("yoy_pct") is not None else (pt.get("yoy_note") or "–")
        else:
            q = rev = rvy = pat = pty = "FAILED"
        fl = c["filings"]
        fcount = len(fl["value"]["items"]) if fl["ok"] else "FAILED"
        rp = c["results_pdf"]
        tp = c["transcript_pdf"]
        rps = f"{rp['value']['pages']}p, {_fmt(rp['value']['chars'])} chars" if rp.get("ok") else "FAILED"
        tps = f"{tp['value']['pages']}p, {_fmt(tp['value']['chars'])} chars" if tp.get("ok") else "FAILED"
        L.append(f"| {c['ticker']} | {close} | {bars} | {q} | {rev} | {rvy} | {pat} | {pty} | {fcount} | {rps} | {tps} |")
    L.append("")

    for c in run["companies"]:
        L += [f"## {c['ticker']}", ""]
        if not c["resolve"]["ok"]:
            L += [f"- Resolve failed: {c['resolve']['error']}", ""]
            continue
        i = c["resolve"]["value"]
        L.append(f"- **Identity:** {i['name']} · NSE `{i['symbol']}` · BSE `{i['bse_code']}` · ISIN `{i['isin']}`")
        px = c["prices"]
        if px["ok"]:
            v = px["value"]
            s = v["summary"]
            L.append(f"- **Prices** ({v['meta']['source']}): {s['bars']} daily bars {v['first']} → {s['date']}; "
                     f"close {_fmt(s['close'], 2)} ({_pct(s['change_pct'])} on the day); "
                     f"52w range {_fmt(s['low_52w'], 2)}–{_fmt(s['high_52w'], 2)}; "
                     f"data checks: {', '.join(v['meta']['notes']) or 'clean'}"
                     + ("; last bar is provisional (Yahoo had not yet published the daily bar)" if v["provisional_last"] else "")
                     + (f"; cross-check vs screener's quoted price {_fmt(v['screener_price'], 2)}: "
                        f"{v['diff_vs_screener_pct']:+.2f}%" if v["diff_vs_screener_pct"] is not None else ""))
        else:
            L.append(f"- **Prices:** FAILED: {px['error']}")
        res = c["results"]
        if res["ok"]:
            v = res["value"]
            L.append(f"- **Latest results** ({v['basis']}, {v['units']}): quarter ended {v['quarter_end']}, "
                     f"compared with {v['prev_quarter_end']} (QoQ) and {v['year_ago_quarter_end']} (YoY)"
                     + (" · **lender format detected**" if v["lender"] else ""))
            L.append("")
            L.append("  | Metric | Value | QoQ | YoY |")
            L.append("  |---|---|---|---|")
            for k, m in v["metrics"].items():
                if "qoq_pct" in m:
                    qoq = _pct(m["qoq_pct"]) if m["qoq_pct"] is not None else (m["qoq_note"] or "–")
                    yoy = _pct(m["yoy_pct"]) if m["yoy_pct"] is not None else (m["yoy_note"] or "–")
                    L.append(f"  | {k} | {_fmt(m['value'], 2 if k == 'eps' else 0)} | {qoq} | {yoy} |")
                else:
                    L.append(f"  | {k} | {m['value']} | | |")
            L.append("")
        else:
            L.append(f"- **Results:** FAILED: {res['error']}")
        fu = c["fundamentals"]
        if fu["ok"]:
            v = fu["value"]
            L.append(f"- **Statements:** {v['quarters']} quarters, {v['years_pl']} years P&L, {v['years_bs']} balance sheets, "
                     f"{v['years_cf']} cash-flow years, {v['years_ratios']} ratio years, {v['shareholding_q']} shareholding quarters. "
                     f"Market cap {v['mcap']}, P/E {v['pe']}.")
            L.append(f"- **Documents found:** {v['annual_reports']} annual reports, {v['concalls']} concalls "
                     f"({v['transcripts']} with transcripts).")
        else:
            L.append(f"- **Statements:** FAILED: {fu['error']}")
        fl = c["filings"]
        if fl["ok"]:
            v = fl["value"]
            L.append(f"- **Filings, last 7 days:** {len(v['items'])} found. Source status: "
                     + "; ".join(f"{k} = {s}" for k, s in v["status"].items()))
            for it in v["items"][:5]:
                L.append(f"  - {it['ts'][:16]} · {it['subject'][:110]} ({', '.join(it['sources'])})")
            if v["coverage_note"]:
                L.append(f"  - _Coverage:_ {v['coverage_note']}")
        else:
            L.append(f"- **Filings:** FAILED: {fl['error']}")
        for label, key in (("Results PDF", "results_pdf"), ("Concall transcript", "transcript_pdf")):
            d = c[key]
            if d.get("ok"):
                v = d["value"]
                if key == "transcript_pdf":
                    td = c.get("transcript_doc") or {}
                    extra = f" ({(td.get('title') or '')[:80]}, {td.get('date')}, via {td.get('via')})"
                    for s in td.get("skipped") or []:
                        L.append(f"- **Skipped newer transcript filing** ({s.get('date')}): {s.get('reason')}"
                                 + (f"; it points to {', '.join(s['points_to'])}" if s.get("points_to") else ""))
                else:
                    rd = c.get("results_doc") or {}
                    extra = f" ({rd.get('kind', '').replace('_', ' ')}: {rd.get('title', '')[:80]})"
                L.append(f"- **{label}{extra}:** {v['kb']:,} KB, {v['pages']} pages, {v['chars']:,} characters via {v['method']}, "
                         f"status `{v['status']}`. Quote check found a sample line on page {v['quote_check_page']}. "
                         f"Sample: “{v['sample']}”")
            else:
                L.append(f"- **{label}:** FAILED: {d.get('error')}")
        L.append("")
    L += ["## What failed or is limited", ""] + [f"- {x}" for x in run["problems"]] + [""]
    return "\n".join(L)


def run(tickers: list[str] | None = None) -> Path:
    tickers = tickers or DEFAULT
    started = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = {"started": started, "rss": filings.poll_rss()}
    out["rss"] = "; ".join(f"{k}: {v}" for k, v in out["rss"].items())

    def nifty():
        f = prices.get_index()
        return {"meta": f.meta(), "summary": prices.summary(f.data)}
    out["nifty"] = _step(nifty)
    out["companies"] = [check_company(t) for t in tickers]

    problems = []
    for c in out["companies"]:
        for k in ("resolve", "prices", "results", "fundamentals", "filings", "results_pdf", "transcript_pdf"):
            st = c.get(k)
            if st and not st.get("ok"):
                problems.append(f"{c['ticker']} · {k}: {st.get('error')}")
        fl = c.get("filings", {})
        if fl.get("ok"):
            for src, s in fl["value"]["status"].items():
                if not s.startswith("ok"):
                    problems.append(f"{c['ticker']} · filings source {src}: {s}")
    out["problems"] = problems or ["Nothing failed."]
    REPORT.write_text(render(out), encoding="utf-8")
    REPORT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    return REPORT
