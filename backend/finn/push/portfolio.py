"""Portfolio config: holdings with weights and the investor's category preferences."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("portfolio.json")


@dataclass
class Portfolio:
    name: str
    weights: dict[str, float]
    preferences: dict[str, float] = field(default_factory=dict)
    alert_rules: list = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        return list(self.weights)


def load(path: str | Path = DEFAULT_PATH) -> Portfolio:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    weights = {h["symbol"].upper(): float(h["weight"]) for h in d["holdings"]}
    total = sum(weights.values())
    if abs(total - 1) > 0.02:
        raise ValueError(f"holding weights add up to {total:.3f}, expected 1.0")
    return Portfolio(d.get("name", ""), weights, d.get("preferences", {}), d.get("alert_rules", []))
