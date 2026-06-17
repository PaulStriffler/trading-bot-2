"""Smoke test: config loads correctly."""
from bot.config import load_config


def test_config_loads():
    cfg = load_config()
    assert cfg.starting_balance == 10000
    assert cfg.leverage == 30
    assert cfg.risk_pct == 1.0
    assert set(cfg.symbols) == {"US500", "US30", "US100", "US2000"}
