"""Recompute yearly returns with compounding.

Original backtest risks 1% of the STARTING equity ($100) on every trade,
so yearly percentages are linear on the $10k base. In reality you risk
1% of CURRENT equity → wins/losses scale with the running balance.

This script re-scales each trade's P&L by (equity / starting) at entry
time, then reports both simple and compounded annual returns.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

STARTING = 10_000


def main() -> None:
    csv = Path(__file__).parent / "results" / "trades_8y.csv"
    df = pd.read_csv(csv, parse_dates=["entry_time", "exit_time"]).sort_values("entry_time").reset_index(drop=True)
    df["year"] = df["entry_time"].dt.year

    # --- Simple (non-compounded) — what the original run reports
    simple_yearly = df.groupby("year").agg(
        trades=("year", "count"),
        pnl_simple=("pnl_dollar", "sum"),
    )
    simple_yearly["pct_simple"] = simple_yearly["pnl_simple"] / STARTING * 100

    # --- Compounded: scale each trade by current equity / starting
    equity = STARTING
    compounded_pnl = []
    equity_after = []
    for _, t in df.iterrows():
        scaled = float(t["pnl_dollar"]) * (equity / STARTING)
        compounded_pnl.append(scaled)
        equity += scaled
        equity_after.append(equity)
    df["pnl_compound"] = compounded_pnl
    df["equity_after"] = equity_after

    # Equity at start of each year (= equity at end of previous year, or STARTING)
    df["equity_before"] = [STARTING] + equity_after[:-1]
    year_starts = df.groupby("year").first()["equity_before"]
    year_ends = df.groupby("year").last()["equity_after"]

    yearly = pd.DataFrame({
        "trades": df.groupby("year").size(),
        "equity_start": year_starts.round(0).astype(int),
        "equity_end": year_ends.round(0).astype(int),
        "pnl_$": (year_ends - year_starts).round(0).astype(int),
        "return_%": ((year_ends / year_starts - 1) * 100).round(1),
        "pct_simple": simple_yearly["pct_simple"].round(1),
    })

    print("=" * 70)
    print(f"YEARLY RETURNS — 8-Year Backtest · $10k Start · 1 % Risk · 1:30 Hebel")
    print("=" * 70)
    print(yearly.to_string())

    total_return_compound = (equity / STARTING - 1) * 100
    total_return_simple = df["pnl_dollar"].sum() / STARTING * 100
    print("\n" + "-" * 70)
    print(f"Total Return (NON-compound, 1 % of $10k always): {total_return_simple:+.2f}%   → ${df['pnl_dollar'].sum():+,.0f}")
    print(f"Total Return (COMPOUND, 1 % of current equity):  {total_return_compound:+.2f}%   → ${equity - STARTING:+,.0f}")
    print(f"End Equity (compound): ${equity:,.0f}")
    print("-" * 70)

    # CAGR (compound annual growth rate)
    n_years = (df["entry_time"].max() - df["entry_time"].min()).days / 365.25
    cagr = (equity / STARTING) ** (1 / n_years) - 1
    print(f"CAGR over {n_years:.1f} years: {cagr*100:.2f}%/year (compound)")

    out_csv = Path(__file__).parent / "results" / "yearly_compounded.csv"
    yearly.to_csv(out_csv)
    print(f"\nSaved: {out_csv}")


if __name__ == "__main__":
    main()
