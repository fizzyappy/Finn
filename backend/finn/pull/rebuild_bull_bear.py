"""Rebuild the fact pool and bull/bear section of every cached research result, without re-reading
any source (tables, ledger and dodged answers come from the cache). Used after a change to the
fact rules. Run: python -m finn.pull.rebuild_bull_bear"""
from __future__ import annotations

from ..store import store
from . import narrative


def main() -> None:
    conn = store().conn
    keys = [k for (k,) in conn.execute("SELECT key FROM cache WHERE ns='research'").fetchall()]
    newest: dict[str, str] = {}
    for k in keys:                       # newest cache entry per ticker only
        t = k.split("|")[0]
        newest[t] = max(newest.get(t, ""), k)
    for t, k in sorted(newest.items()):
        hit = store().get("research", k)
        if not hit:
            continue
        r = hit[0]
        S = r["sections"]
        tb = {"snapshot": S.get("snapshot") or {}, "trajectory": S.get("trajectory") or {},
              "balance_sheet": S.get("balance_sheet") or {}, "cash_quality": S.get("cash_quality") or {}}
        facts = narrative.fact_pool(tb, S.get("promise_ledger"), S.get("dodged_questions") or [])
        bb = narrative.bull_bear(facts, r.get("name") or t)
        if not (bb["bull"] or bb["bear"]):
            print(t, "kept the previous bull/bear (model gave nothing usable)")
            continue
        S["facts"], S["bull_bear"] = facts, bb
        store().put("research", k, r, "pull engine")
        print(t, f"bull {len(bb['bull'])} bear {len(bb['bear'])} removed {len(bb['removed'])}")


if __name__ == "__main__":
    main()
