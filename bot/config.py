"""Load strategy configuration from YAML."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "strategy.yaml"


@dataclass(frozen=True)
class Config:
    raw: dict[str, Any]

    @property
    def starting_balance(self) -> float:
        return float(self.raw["account"]["starting_balance_eur"])

    @property
    def leverage(self) -> int:
        return int(self.raw["account"]["leverage"])

    @property
    def risk_pct(self) -> float:
        return float(self.raw["account"]["risk_per_trade_pct"])

    @property
    def symbols(self) -> list[str]:
        return list(self.raw["symbols"])


def load_config(path: Path = CONFIG_PATH) -> Config:
    with path.open("r", encoding="utf-8") as f:
        return Config(raw=yaml.safe_load(f))
