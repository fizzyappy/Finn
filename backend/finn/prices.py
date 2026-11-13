"""End-of-day prices and volume.

Primary: yfinance (Indian tickers use .NS; BSE-only companies use .BO).
Fallback: Yahoo's chart JSON directly, so a yfinance breaking change (it happens
several times a year) does not take the app down.
Every series passes data-quality checks before anyone uses it.

Bars are plain dicts (JSON-friendly): {date, open, high, low, close, adj_close, volume}.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from . import http
from .store import Fetched, store
from .symbols import resolve

IST = timezone(timedelta(hours=5, minutes=30))
NIFTY = "^NSEI"
VALID_PERIODS = {"5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"}


def _f(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _via_yfinance(yticker: str, period: str) -> list[dict]:
    import yfinance as yf

    df = yf.Ticker(yticker).history(period=period, interval="1d", auto_adjust=False, actions=False)
    if df is None or df.empty:
        return []
    bars = []
    for ts, r in df.iterrows():
        bars.append({
            "date": ts.date().isoformat(),
            "open": _f(r.get("Open")), "high": _f(r.get("High")), "low": _f(r.get("Low")),
            "close": _f(r.get("Close")), "adj_close": _f(r.get("Adj Close", r.get("Close"))),
            "volume": int(_f(r.get("Volume")) or 0),
        })
    return bars


def parse_chart_json(data: dict) -> list[dict]:
    res = (data.get("chart") or {}).get("result") or []
    if not res:
        err = (data.get("chart") or {}).get("error")
        raise http.SourceError(f"Yahoo chart: no result ({err})")
    res = res[0]
    q = res["indicators"]["quote"][0]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    bars = []
    for i, ts in enumerate(res.get("timestamp") or []):
        d = datetime.fromtimestamp(ts, tz=IST).date().isoformat()
        close = _f(q["close"][i])
        bars.append({
            "date": d, "open": _f(q["open"][i]), "high": _f(q["high"][i]), "low": _f(q["low"][i]),
            "close": close, "adj_close": _f(adj[i]) if adj else close,
            "volume": int(_f(q["volume"][i]) or 0),
        })
    return bars


def _via_chart_api(yticker: str, period: str) -> list[dict]:
    last: Exception | None = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            data = http.get_json(f"https://{host}/v8/finance/chart/{yticker}",
                                 params={"range": period, "interval": "1d"})
            return parse_chart_json(data)
        except Exception as e:  # noqa: BLE001
            last = e
    raise http.SourceError(f"Yahoo chart failed: {last}")


def clean(bars: list[dict]) -> list[dict]:
    """Drop rows without a close, keep the last row per date, sort by date."""
    by_date = {}
    for b in bars:
        if b.get("close") is not None and b["close"] > 0:
            for k in ("open", "high", "low", "close", "adj_close"):
                if b.get(k) is not None:
                    b[k] = round(b[k], 2)
            by_date[b["date"]] = b
    return [by_date[d] for d in sorted(by_date)]


def check_bars(bars: list[dict], today: date | None = None) -> list[str]:
    """Plain-language data-quality warnings (empty list = clean)."""
    issues = []
    if not bars:
        return ["no data"]
    today = today or datetime.now(IST).date()
    dates = [b["date"] for b in bars]
    if len(set(dates)) != len(dates):
        issues.append("duplicate dates")
    if dates != sorted(dates):
        issues.append("dates out of order")
    bad = [b["date"] for b in bars if b["high"] is not None and b["low"] is not None and b["high"] < b["low"]]
    if bad:
        issues.append(f"high below low on {len(bad)} day(s)")
    outside = [b["date"] for b in bars if None not in (b["high"], b["low"], b["close"])
               and not (b["low"] * 0.999 <= b["close"] <= b["high"] * 1.001)]
    if outside:
        issues.append(f"close outside the day's range on {len(outside)} day(s)")
    zero = sum(1 for b in bars if not b["volume"])
    if zero > max(2, len(bars) * 0.05):
        issues.append(f"zero volume on {zero} of {len(bars)} days")
    ds = [date.fromisoformat(d) for d in dates]
    gaps = [(a, b) for a, b in zip(ds, ds[1:]) if (b - a).days > 7]
    if gaps:
        issues.append(f"{len(gaps)} gap(s) longer than a week, first after {gaps[0][0]}")
    age = (today - ds[-1]).days
    if age > 5:
        issues.append(f"latest bar is {age} days old ({ds[-1]})")
    jumps = [(b["date"], round((b["close"] / a["close"] - 1) * 100, 1))
             for a, b in zip(bars, bars[1:]) if a["close"] and abs(b["close"] / a["close"] - 1) > 0.35]
    if jumps:
        issues.append(f"{len(jumps)} one-day move(s) over 35% (split/bonus or bad tick?), e.g. {jumps[0]}")
    return issues


MARKET_CLOSE = (15, 30)


def provisional_bar(meta: dict, now: datetime | None = None) -> dict | None:
    """Yahoo often publishes the day's daily bar late (close = null for hours after
    the close). Its quote block already has the session's last trade, high, low and
    volume. Once the session is over, use that as a bar marked provisional."""
    t = meta.get("regularMarketTime")
    price = _f(meta.get("regularMarketPrice"))
    if not t or price is None:
        return None
    when = datetime.fromtimestamp(t, tz=IST)
    now = now or datetime.now(IST)
    closed = when.date() < now.date() or (now.hour, now.minute) >= MARKET_CLOSE
    if not closed:
        return None
    return {"date": when.date().isoformat(), "open": None,
            "high": _f(meta.get("regularMarketDayHigh")), "low": _f(meta.get("regularMarketDayLow")),
            "close": price, "adj_close": price, "volume": int(_f(meta.get("regularMarketVolume")) or 0),
            "provisional": True}


def _patch_latest(yticker: str, bars: list[dict]) -> bool:
    """Append today's provisional bar if the daily series is missing it."""
    try:
        data = http.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{yticker}",
                             params={"range": "1d", "interval": "1d"})
        meta = data["chart"]["result"][0]["meta"]
    except Exception:  # noqa: BLE001 - patching is best-effort
        return False
    pb = provisional_bar(meta)
    if pb and (not bars or pb["date"] > bars[-1]["date"]):
        bars.append(clean([pb])[0])
        return True
    return False


def _fetch(yticker: str, period: str) -> tuple[list[dict], str]:
    errors = []
    for fn, label in ((_via_yfinance, "yfinance"), (_via_chart_api, "yahoo-chart")):
        try:
            bars = clean(fn(yticker, period))
            if bars:
                patched = _patch_latest(yticker, bars)
                return bars, f"{label}:{yticker}" + (" + provisional last bar from Yahoo quote" if patched else "")
            errors.append(f"{label}: empty")
        except Exception as e:  # noqa: BLE001 - try the next source
            errors.append(f"{label}: {type(e).__name__}: {str(e)[:120]}")
    raise LookupError(f"no price data for {yticker}: {'; '.join(errors)}")


def get_bars(yticker: str, period: str = "1y", refresh: bool = False) -> Fetched:
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of {sorted(VALID_PERIODS)}")
    f = store().cached("prices", f"{yticker}|{period}", lambda: _fetch(yticker, period), refresh=refresh)
    f.notes = check_bars(f.data)
    return f


def get_prices(ticker: str, period: str = "1y", refresh: bool = False) -> Fetched:
    """Daily bars for any NSE symbol or BSE code."""
    inst = resolve(ticker)
    candidates = [inst.yahoo] + ([inst.yahoo_bse] if inst.yahoo_bse and inst.symbol else [])
    last: Exception | None = None
    for y in candidates:
        try:
            return get_bars(y, period, refresh=refresh)
        except LookupError as e:
            last = e
    raise LookupError(str(last))


def get_index(symbol: str = NIFTY, period: str = "1y", refresh: bool = False) -> Fetched:
    return get_bars(symbol, period, refresh=refresh)


def summary(bars: list[dict]) -> dict:
    """Latest close, day change and 52-week range, computed here (never by an LLM)."""
    if len(bars) < 2:
        raise ValueError("need at least two bars")
    last, prev = bars[-1], bars[-2]
    year = bars[-252:]
    return {
        "date": last["date"],
        "close": round(last["close"], 2),
        "prev_close": round(prev["close"], 2),
        "change_pct": round((last["close"] / prev["close"] - 1) * 100, 2),
        "volume": last["volume"],
        "high_52w": round(max(b["high"] for b in year if b["high"] is not None), 2),
        "low_52w": round(min(b["low"] for b in year if b["low"] is not None), 2),
        "bars": len(bars),
    }
