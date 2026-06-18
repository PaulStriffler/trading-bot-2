"""Run the 3-week POC backtest over all 4 symbols and print a summary."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch
from .engine import simulate
from .strategy import atr, build_setup, find_daily_sweeps, find_entry, weekly_bias

warnings.filterwarnings("ignore")

ACCOUNT = 10_000
RISK_PCT = 1.0
WEEKS = 3
MIN_CONFLUENCES = 2


def run() -> list:
    results = []
    log_lines = []

    for symbol in SYMBOL_MAP:
        log_lines.append(f"\n=== {symbol} ===")
        bars = fetch(symbol, weeks=WEEKS)
        bias = weekly_bias(bars.w1)
        log_lines.append(f"Weekly bias: {bias}")
        if bias == "none":
            log_lines.append("→ no bias, skip")
            continue

        sweeps = find_daily_sweeps(bars.d1, bias, window=WEEKS * 7 + 5)
        log_lines.append(f"Daily sweeps found: {len(sweeps)}")

        atr_series = atr(bars.h4, period=14)

        for sweep in sweeps:
            atr_val = float(atr_series.loc[atr_series.index <= sweep.time].iloc[-1]) if (atr_series.index <= sweep.time).any() else float(atr_series.iloc[-1])
            setup = build_setup(bars.h4, sweep, symbol, min_confluences=MIN_CONFLUENCES)
            if setup is None:
                log_lines.append(f"  sweep@{sweep.time.date()} {sweep.direction}: no setup (confluences fail)")
                continue
            trade = find_entry(bars.h1, setup, atr_val)
            if trade is None:
                log_lines.append(f"  sweep@{sweep.time.date()} {sweep.direction}: setup ok ({'+'.join(setup.confluences)}), no entry trigger")
                continue
            result = simulate(trade, bars.h1, balance=ACCOUNT, risk_pct=RISK_PCT)
            results.append(result)
            log_lines.append(f"  TRADE {trade.direction} @ {trade.entry_time}  exit={result.exit_reason}  R={result.rr_realized:.2f}  $={result.pnl_dollar:+.2f}  [{result.confluences}]")

    print("\n".join(log_lines))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY — 3-Week POC Backtest")
    print("=" * 60)
    print(f"Account: ${ACCOUNT:,}  Risk: {RISK_PCT}%/trade  Period: last {WEEKS} weeks")
    print(f"Total trades: {len(results)}")
    if results:
        total_pnl = sum(r.pnl_dollar for r in results)
        wins = sum(1 for r in results if r.pnl_dollar > 0)
        total_r = sum(r.rr_realized for r in results)
        print(f"Winners: {wins} / {len(results)}  ({100*wins/len(results):.0f}% winrate)")
        print(f"Total P&L: ${total_pnl:+,.2f}  ({100*total_pnl/ACCOUNT:+.2f}% of account)")
        print(f"Total R: {total_r:+.2f}")
        print(f"End equity: ${ACCOUNT + total_pnl:,.2f}")

        # Per-symbol breakdown
        df = pd.DataFrame([r.__dict__ for r in results])
        print("\nBy symbol:")
        per_sym = df.groupby("symbol").agg(trades=("symbol", "count"), pnl=("pnl_dollar", "sum"), R=("rr_realized", "sum"))
        print(per_sym.to_string())

        # Save trade log
        out = Path(__file__).parent / "results"
        out.mkdir(exist_ok=True)
        df.to_csv(out / "trades.csv", index=False)
        print(f"\nTrade log: {out / 'trades.csv'}")
    else:
        print("→ No trades in this 3-week window (expected for so short a sample).")

    return results


if __name__ == "__main__":
    sys.exit(0 if run() is not None else 1)
