"""End-of-day price and volume alerts, measured against each stock's own normal.

For every trading day:
  return          close / previous close - 1
  market return   the same for Nifty 50
  beta            how much the stock usually moves with the market (previous 120 days)
  own move        return - beta x market return   (the part the market does not explain)
  sigma           the usual size of the own move (standard deviation, previous 60 days)
  z               own move / sigma                 ("a 3-sigma day" = unusual for THIS stock)
  volume ratio    volume / average of the previous 20 days (today excluded)

Rules combine thresholds on these (all conditions must hold). Presets cover the
common cases; a custom rule is a dict. `backtest` replays a rule over past days so
the investor can see how often it would have fired before switching it on.
Filings made before a move are shown as "filed before", never as the cause.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from .. import prices
from ..filings import IST

BETA_WINDOW, SIGMA_WINDOW, VOL_WINDOW = 120, 60, 20


@dataclass
class Rule:
    name: str
    label: str
    min_abs_z: float | None = None
    min_vol_x: float | None = None
    min_abs_ret_pct: float | None = None
    direction: str = "any"            # any | up | down

    def fires(self, row: dict) -> bool:
        if row.get("z") is None and self.min_abs_z is not None:
            return False
        if self.min_abs_z is not None and abs(row["z"]) < self.min_abs_z:
            return False
        if self.min_vol_x is not None and (row.get("vol_x") is None or row["vol_x"] < self.min_vol_x):
            return False
        if self.min_abs_ret_pct is not None and abs(row["ret_pct"]) < self.min_abs_ret_pct:
            return False
        if self.direction == "up" and row["ret_pct"] <= 0:
            return False
        if self.direction == "down" and row["ret_pct"] >= 0:
            return False
        return any(x is not None for x in (self.min_abs_z, self.min_vol_x, self.min_abs_ret_pct))


PRESETS = {
    "unusual_move": Rule("unusual_move", "Move unusual for this stock (2.5 sigma after the market)", min_abs_z=2.5),
    "volume_spike": Rule("volume_spike", "Volume at least 2.5x its 20-day average", min_vol_x=2.5),
    "move_on_volume": Rule("move_on_volume", "Unusual move (2 sigma) on heavy volume (1.8x)", min_abs_z=2.0, min_vol_x=1.8),
    "big_day": Rule("big_day", "Price moved 5% or more", min_abs_ret_pct=5.0),
}


def rule_from(spec: str | dict) -> Rule:
    if isinstance(spec, str):
        if spec not in PRESETS:
            raise ValueError(f"unknown preset '{spec}'. Presets: {sorted(PRESETS)}")
        return PRESETS[spec]
    allowed = {"name", "label", "min_abs_z", "min_vol_x", "min_abs_ret_pct", "direction"}
    bad = set(spec) - allowed
    if bad:
        raise ValueError(f"unknown rule fields {sorted(bad)}")
    return Rule(**{"name": "custom", "label": "Custom rule", **spec})


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _stdev(xs: list[float]) -> float:
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def compute_series(bars: list[dict], market: list[dict]) -> list[dict]:
    """Per-day measures for one stock. Days without a market bar are skipped."""
    mkt = {b["date"]: b["close"] for b in market}
    rows: list[dict] = []
    prev_close = None
    for b in bars:
        if prev_close is None or b["date"] not in mkt:
            prev_close = b["close"] if b["date"] in mkt else prev_close
            continue
        prev_mkt = next((mkt[r["date"]] for r in reversed(rows)), None) if rows else None
        rows.append({"date": b["date"], "close": b["close"], "volume": b["volume"],
                     "ret": b["close"] / prev_close - 1,
                     "mret": (mkt[b["date"]] / prev_mkt - 1) if prev_mkt else None,
                     "provisional": bool(b.get("provisional"))})
        prev_close = b["close"]
    out = []
    for i, r in enumerate(rows):
        row = {"date": r["date"], "close": r["close"], "volume": r["volume"], "provisional": r["provisional"],
               "ret_pct": round(r["ret"] * 100, 2),
               "mkt_ret_pct": round(r["mret"] * 100, 2) if r["mret"] is not None else None,
               "beta": None, "own_move_pct": None, "sigma_pct": None, "z": None, "vol_x": None}
        hist = [x for x in rows[max(0, i - BETA_WINDOW):i] if x["mret"] is not None]
        if len(hist) >= 60 and r["mret"] is not None:
            mx, my = _mean([h["mret"] for h in hist]), _mean([h["ret"] for h in hist])
            var = sum((h["mret"] - mx) ** 2 for h in hist)
            beta = sum((h["mret"] - mx) * (h["ret"] - my) for h in hist) / var if var else 0.0
            beta = max(-1.0, min(4.0, beta))
            own_hist = [h["ret"] - beta * h["mret"] for h in hist[-SIGMA_WINDOW:]]
            sigma = _stdev(own_hist)
            own = r["ret"] - beta * r["mret"]
            row.update({"beta": round(beta, 2), "own_move_pct": round(own * 100, 2),
                        "sigma_pct": round(sigma * 100, 2), "z": round(own / sigma, 2) if sigma else None})
        vols = [x["volume"] for x in rows[max(0, i - VOL_WINDOW):i] if x["volume"]]
        if len(vols) >= 10 and r["volume"]:
            row["vol_x"] = round(r["volume"] / _mean(vols), 2)
        out.append(row)
    return out


def describe(symbol: str, row: dict) -> str:
    parts = [f"{symbol} {row['ret_pct']:+.1f}%"]
    if row.get("mkt_ret_pct") is not None:
        parts.append(f"(Nifty {row['mkt_ret_pct']:+.1f}%)")
    if row.get("z") is not None:
        parts.append(f"- {abs(row['z']):.1f} sigma {'above' if row['z'] > 0 else 'below'} its normal day "
                     f"after the market move (usual swing {row['sigma_pct']:.1f}%)")
    if row.get("vol_x") is not None:
        parts.append(f"; volume {row['vol_x']:.1f}x its 20-day average")
    if row.get("provisional"):
        parts.append(" [provisional close]")
    return " ".join(parts).replace(" ;", ";")


def portfolio_series(symbols: list[str], period: str = "1y") -> tuple[dict[str, list[dict]], dict]:
    """Series for every holding + data status."""
    market = prices.get_index(period=period)
    out, status = {}, {"nifty": {**market.meta(), "last_date": market.data[-1]["date"]}}
    for s in symbols:
        try:
            f = prices.get_prices(s, period)
            out[s] = compute_series(f.data, market.data)
            status[s] = {"source": f.source, "last_date": f.data[-1]["date"], "stale": f.stale,
                         "provisional": bool(f.data[-1].get("provisional")), "checks": f.notes}
        except Exception as e:  # noqa: BLE001
            status[s] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
    return out, status


def fired(series: dict[str, list[dict]], rules: list[Rule], dates: set[str] | None = None) -> list[dict]:
    out = []
    for sym, rows in series.items():
        for row in rows:
            if dates is not None and row["date"] not in dates:
                continue
            for rule in rules:
                if rule.fires(row):
                    out.append({"symbol": sym, "date": row["date"], "rule": rule.name, "rule_label": rule.label,
                                "text": describe(sym, row), "measures": row})
    return sorted(out, key=lambda a: (a["date"], a["symbol"]), reverse=True)


def backtest(rule: Rule | str | dict, series: dict[str, list[dict]], days: int = 90) -> dict:
    """How often would this rule have fired over the last `days` trading days?"""
    rule = rule if isinstance(rule, Rule) else rule_from(rule)
    all_dates = sorted({r["date"] for rows in series.values() for r in rows})[-days:]
    hits = fired(series, [rule], set(all_dates))
    per_symbol: dict[str, list[str]] = {}
    for h in hits:
        per_symbol.setdefault(h["symbol"], []).append(h["date"])
    weeks = max(1.0, len(all_dates) / 5)
    return {"rule": asdict(rule), "trading_days": len(all_dates),
            "from": all_dates[0] if all_dates else None, "to": all_dates[-1] if all_dates else None,
            "fires_total": len(hits), "fires_per_week": round(len(hits) / weeks, 1),
            "per_symbol": {k: sorted(v) for k, v in sorted(per_symbol.items(), key=lambda kv: -len(kv[1]))},
            "quiet_symbols": sorted(set(series) - set(per_symbol)),
            "examples": [{"symbol": h["symbol"], "date": h["date"], "text": h["text"]} for h in hits[:5]]}


def link_filings(alert: dict, filings_by_symbol: dict[str, list[dict]], lookback_days: int = 3) -> list[dict]:
    """Filings by the same company in the days before the move (up to that day's close).
    Shown as 'filed before this move' - timing only, never a claim of cause."""
    day = datetime.fromisoformat(alert["date"]).replace(hour=15, minute=30, tzinfo=IST)
    start = day - timedelta(days=lookback_days)
    out = []
    for f in filings_by_symbol.get(alert["symbol"], []):
        try:
            ts = datetime.fromisoformat(f["ts"])
        except (TypeError, ValueError):
            continue
        if start <= ts <= day:
            out.append({"ts": f["ts"], "title": f.get("headline") or f.get("subject"), "url": f.get("url"),
                        "category": f.get("category"), "treatment": f.get("treatment")})
    return sorted(out, key=lambda x: x["ts"], reverse=True)
