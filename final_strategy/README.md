# Final Strategy — ICT/SMC Multi-Timeframe v3

Self-contained final version of Paul's trading strategy. All code and the strategy specification live here.

## Files

| File | Purpose |
|---|---|
| [`STRATEGY.md`](STRATEGY.md) | The complete strategy specification (German) |
| [`strategy.py`](strategy.py) | v3 implementation: `weekly_bias_v3`, `find_ob_4h`, `find_entry_v3` (the LEAVE→RE-ENTER→FVG→BOS sequence) |
| [`strategy_base.py`](strategy_base.py) | Shared low-level helpers: `atr`, `find_daily_sweeps`, dataclasses `Sweep`/`Setup`/`Trade` |
| [`engine.py`](engine.py) | Trade simulator with 3 partial TPs, SL→BE at TP1, 1:30 leverage check |
| [`data.py`](data.py) | yfinance data loader for US500/US30/US100/US2000 (W1, D1, H4 resampled, H1) |
| [`run.py`](run.py) | 2-year backtest entry point |
| [`screenshots.py`](screenshots.py) | TradingView-style 1H annotated PNG generator |

## Quickstart

```bash
# from repo root
python -m final_strategy.run
python -m final_strategy.screenshots
```

Output:
- `backtest/quick/results/trades_v3_2y.csv` — trade log
- `backtest/quick/results/pngs_v3/` — one 1280×720 PNG per trade

## Current results (2 years, 1H)

- **61 Trades** · 60.7 % Winrate
- **+17.32 %** total return (compound on $10k)
- **CAGR: 8.95 %/Jahr**
- **Max DD: -3.9 %**

By symbol:
| Symbol | Trades | Winrate | P&L | R |
|---|---|---|---|---|
| US100 | 16 | 75 % | +$723 | +7.23 |
| US30 | 14 | 64 % | +$377 | +3.77 |
| US2000 | 15 | 47 % | +$304 | +3.04 |
| US500 | 16 | 56 % | +$245 | +2.45 |

## Data limitation

yfinance gives 1H data for the last ~730 days only. For a 5-year backtest with real 1H entries, MT5 export is required.

## Account context

| Setting | Value |
|---|---|
| Broker | FTMO Funded Swing $10k (Eval 1) |
| Risk per trade | 1 % = $100 |
| Leverage | 1:30 |
| 3 TPs (partials) | 33 % / 33 % / 34 % |
| SL → Break-even | after TP1 |
