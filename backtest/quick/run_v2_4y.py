"""4-year backtest of strategy v2 (strict OB-tap + sub-confluence + BOS).

$10k account · 1 % risk · 1:30 leverage · Daily-variant on yfinance data.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch_long
from .engine import simulate
from .strategy import atr, build_setup, find_daily_sweeps
from .strategy_v2 import find_strict_entry, weekly_bias_strict

warnings.filterwarnings("ignore")

ACCOUNT = 10_000
RISK_PCT = 1.0
LEVERAGE = 30.0
YEARS = 4
MIN_CONFLUENCES = 2


def run() -> None:
    all_results = []
    diag = {"bias_none": 0, "no_sweep_in_week": 0, "no_setup": 0, "no_strict_entry": 0, "trades": 0}

    for symbol in SYMBOL_MAP:
        print(f"\n=== {symbol} ===")
        bars = fetch_long(symbol, years=YEARS + 1)
        atr_series = atr(bars.d1, period=14)

        for wi in range(8, len(bars.w1)):
            w_slice = bars.w1.iloc[: wi + 1]
            bias = weekly_bias_strict(w_slice)
            if bias == "none":
                diag["bias_none"] += 1
                continue
            week_start = bars.w1.index[wi]
            week_end = bars.w1.index[wi + 1] if wi + 1 < len(bars.w1) else bars.d1.index[-1]
            d_ctx_start = max(0, bars.d1.index.get_indexer([week_start], method="nearest")[0] - 10)
            d_ctx = bars.d1.iloc[d_ctx_start: bars.d1.index.get_indexer([week_end], method="nearest")[0]]
            sweeps = find_daily_sweeps(d_ctx, bias, window=len(d_ctx))
            in_week = [s for s in sweeps if week_start <= s.time < week_end]
            if not in_week:
                diag["no_sweep_in_week"] += 1
                continue

            for sweep in in_week:
                atr_val = float(atr_series.loc[atr_series.index <= sweep.time].iloc[-1])
                setup = build_setup(bars.d1, sweep, symbol, min_confluences=MIN_CONFLUENCES)
                if setup is None:
                    diag["no_setup"] += 1
                    continue
                trade = find_strict_entry(bars.d1, setup, atr_val)
                if trade is None:
                    diag["no_strict_entry"] += 1
                    continue
                if all_results and all_results[-1].symbol == symbol and trade.entry_time <= all_results[-1].exit_time:
                    continue
                result = simulate(trade, bars.d1, balance=ACCOUNT, risk_pct=RISK_PCT, leverage=LEVERAGE)
                if result.exit_reason == "margin_rejected":
                    continue
                all_results.append(result)
                diag["trades"] += 1

        per_sym = [r for r in all_results if r.symbol == symbol]
        print(f"  trades: {len(per_sym)}")

    # Trim to exactly 4-year window from today
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=YEARS * 365)
    all_results = [r for r in all_results if pd.Timestamp(r.entry_time).tz_localize(None) >= cutoff]

    print("\n" + "=" * 70)
    print(f"SUMMARY — v2 (strict OB+sub+BOS) · {YEARS}-Year Backtest")
    print("=" * 70)
    print(f"Account: ${ACCOUNT:,}  Risk: {RISK_PCT}%  Leverage: 1:{int(LEVERAGE)}")
    print(f"Total trades: {len(all_results)}")
    print(f"Diagnostics — skipped: bias-none={diag['bias_none']}, no-sweep={diag['no_sweep_in_week']}, "
          f"no-setup={diag['no_setup']}, no-strict-entry={diag['no_strict_entry']}")

    if not all_results:
        print("→ No trades passed the strict filter.")
        return

    df = pd.DataFrame([r.__dict__ for r in all_results])
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    df = df.sort_values("entry_time").reset_index(drop=True)
    df["year"] = df["entry_time"].dt.year

    # Compound walk
    equity = ACCOUNT
    eq_after = []
    for _, t in df.iterrows():
        equity += t["pnl_dollar"] * (equity / ACCOUNT)
        eq_after.append(equity)
    df["equity"] = eq_after

    wins = int((df["pnl_dollar"] > 0).sum())
    winrate = wins / len(df) * 100
    total_r = df["rr_realized"].sum()
    end_eq = equity
    total_pct = (end_eq / ACCOUNT - 1) * 100
    n_years = (df["entry_time"].max() - df["entry_time"].min()).days / 365.25
    cagr = (end_eq / ACCOUNT) ** (1 / n_years) - 1 if n_years > 0 else 0
    max_dd = (df["equity"] / df["equity"].cummax() - 1).min() * 100

    print(f"Winrate: {winrate:.1f}%   Total R: {total_r:+.2f}")
    print(f"Total Return (compound): {total_pct:+.2f}%   End equity: ${end_eq:,.2f}")
    print(f"CAGR: {cagr*100:+.2f}%/yr   Max Drawdown: {max_dd:.1f}%")

    print("\nBy year:")
    yearly = df.groupby("year").agg(trades=("year", "count"),
                                     wins=("pnl_dollar", lambda s: (s > 0).sum()),
                                     pnl=("pnl_dollar", "sum"),
                                     R=("rr_realized", "sum"))
    yearly["winrate%"] = (yearly["wins"] / yearly["trades"] * 100).round(0)
    print(yearly.to_string())

    print("\nBy symbol:")
    by_sym = df.groupby("symbol").agg(trades=("symbol", "count"),
                                       wins=("pnl_dollar", lambda s: (s > 0).sum()),
                                       pnl=("pnl_dollar", "sum"),
                                       R=("rr_realized", "sum"))
    by_sym["winrate%"] = (by_sym["wins"] / by_sym["trades"] * 100).round(0)
    print(by_sym.to_string())

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    df.drop(columns=["year"]).to_csv(out / "trades_v2_4y.csv", index=False)
    print(f"\nSaved: {out / 'trades_v2_4y.csv'}")


if __name__ == "__main__":
    run()
