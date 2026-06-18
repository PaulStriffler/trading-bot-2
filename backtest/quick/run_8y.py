"""8-year backtest using the daily-only strategy variant.

Same logic as the 3-week POC, but Daily replaces 4H + 1H because
yfinance does not serve intraday data that far back.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch_long
from .engine import simulate
from .strategy import atr, build_setup, find_daily_sweeps, find_entry, weekly_bias

warnings.filterwarnings("ignore")

ACCOUNT = 10_000
RISK_PCT = 1.0
LEVERAGE = 30.0
YEARS = 8
MIN_CONFLUENCES = 2


def run() -> list:
    all_results = []

    for symbol in SYMBOL_MAP:
        print(f"\n=== {symbol} ===")
        bars = fetch_long(symbol, years=YEARS)
        if bars.w1.empty or bars.d1.empty:
            print("  no data")
            continue

        atr_series = atr(bars.d1, period=14)

        # Walk the weekly index — recompute bias at each weekly close, then
        # scan the daily window of that week for sweeps and trade them.
        trades_for_symbol = 0
        skipped_no_setup = 0
        skipped_no_entry = 0

        # We sweep through every week and use the bias known at that point in time
        for wi in range(8, len(bars.w1)):  # need ≥8 weeks for bias
            w_slice = bars.w1.iloc[: wi + 1]
            bias = weekly_bias(w_slice)
            if bias == "none":
                continue

            week_start = bars.w1.index[wi]
            week_end = bars.w1.index[wi + 1] if wi + 1 < len(bars.w1) else bars.d1.index[-1]
            d_window = bars.d1[(bars.d1.index >= week_start) & (bars.d1.index < week_end)]
            if len(d_window) < 4:
                continue
            # Provide context: a wider daily window for sweep detection
            d_context_start = max(0, bars.d1.index.get_indexer([week_start], method="nearest")[0] - 10)
            d_context = bars.d1.iloc[d_context_start: bars.d1.index.get_indexer([week_end], method="nearest")[0]]

            sweeps = find_daily_sweeps(d_context, bias, window=len(d_context))
            for sweep in sweeps:
                if not (week_start <= sweep.time < week_end):
                    continue
                atr_val = float(atr_series.loc[atr_series.index <= sweep.time].iloc[-1])
                setup = build_setup(bars.d1, sweep, symbol, min_confluences=MIN_CONFLUENCES)
                if setup is None:
                    skipped_no_setup += 1
                    continue
                trade = find_entry(bars.d1, setup, atr_val)
                if trade is None:
                    skipped_no_entry += 1
                    continue
                # Skip trades that would re-enter same week as previous open
                if all_results and all_results[-1].symbol == symbol and trade.entry_time <= all_results[-1].exit_time:
                    continue
                result = simulate(trade, bars.d1, balance=ACCOUNT, risk_pct=RISK_PCT, leverage=LEVERAGE)
                all_results.append(result)
                trades_for_symbol += 1

        print(f"  trades: {trades_for_symbol}  (skipped: {skipped_no_setup} no-setup, {skipped_no_entry} no-entry)")

    # ---- Summary ----
    print("\n" + "=" * 70)
    print(f"SUMMARY — {YEARS}-Year Backtest (Daily Variant)")
    print("=" * 70)
    print(f"Account: ${ACCOUNT:,}  Risk: {RISK_PCT}%/trade  Leverage: 1:{int(LEVERAGE)}  Symbols: {', '.join(SYMBOL_MAP)}")
    print(f"Total trades: {len(all_results)}")
    rejected = sum(1 for r in all_results if r.exit_reason == "margin_rejected")
    if rejected:
        print(f"  ⚠ Margin-rejected: {rejected}  (position size exceeded available margin at 1:{int(LEVERAGE)})")

    if not all_results:
        return all_results

    df = pd.DataFrame([r.__dict__ for r in all_results])
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    df = df.sort_values("entry_time").reset_index(drop=True)
    df["equity"] = ACCOUNT + df["pnl_dollar"].cumsum()
    df["year"] = df["entry_time"].dt.year

    total_pnl = df["pnl_dollar"].sum()
    winrate = (df["pnl_dollar"] > 0).mean() * 100
    total_r = df["rr_realized"].sum()
    max_eq = df["equity"].cummax()
    drawdown = (df["equity"] / max_eq - 1)
    max_dd = drawdown.min() * 100

    print(f"Winrate: {winrate:.1f}%   Total R: {total_r:+.2f}")
    print(f"Total P&L: ${total_pnl:+,.2f}  ({100*total_pnl/ACCOUNT:+.2f}% of starting equity)")
    print(f"End equity: ${ACCOUNT + total_pnl:,.2f}   Max Drawdown: {max_dd:.1f}%")

    # Leverage / margin stats
    avg_lev = df["leverage_used"].mean()
    max_lev = df["leverage_used"].max()
    avg_margin = df["margin_required"].mean()
    max_margin = df["margin_required"].max()
    print(f"\nLeverage utilisation: avg {avg_lev:.1f}x  max {max_lev:.1f}x  (cap = 1:{int(LEVERAGE)})")
    print(f"Margin per trade:     avg ${avg_margin:,.0f}  max ${max_margin:,.0f}  (of ${ACCOUNT:,} equity)")

    print("\nBy year:")
    yearly = df.groupby("year").agg(trades=("year", "count"),
                                     wins=("pnl_dollar", lambda s: (s > 0).sum()),
                                     pnl=("pnl_dollar", "sum"),
                                     R=("rr_realized", "sum"))
    yearly["winrate%"] = (yearly["wins"] / yearly["trades"] * 100).round(0)
    print(yearly.to_string())

    print("\nBy symbol:")
    by_sym = df.groupby("symbol").agg(trades=("symbol", "count"),
                                       pnl=("pnl_dollar", "sum"),
                                       R=("rr_realized", "sum"))
    print(by_sym.to_string())

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    df.drop(columns=["year"]).to_csv(out / "trades_8y.csv", index=False)
    yearly.to_csv(out / "yearly_8y.csv")
    print(f"\nFiles: {out / 'trades_8y.csv'}, {out / 'yearly_8y.csv'}")
    return all_results


if __name__ == "__main__":
    sys.exit(0 if run() is not None else 1)
