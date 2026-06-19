"""Parameter sweep over the 8y backtest.

Tests combinations of risk%, min_confluences, TP3 method, and symbol filter.
Reports CAGR, total return, max drawdown and trade count per config.
"""
from __future__ import annotations

import itertools
import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch_long
from .engine import simulate
from .strategy import atr, build_setup, find_daily_sweeps, find_entry, weekly_bias

warnings.filterwarnings("ignore")

ACCOUNT = 10_000
LEVERAGE = 30.0
YEARS = 8


def run_one(risk_pct: float, min_conf: int, tp3_method: str, tp3_r: float,
            symbols: list[str], bias_n: int) -> dict:
    all_results = []
    for symbol in symbols:
        bars = fetch_long(symbol, years=YEARS)
        if bars.w1.empty:
            continue
        atr_series = atr(bars.d1, period=14)

        for wi in range(8, len(bars.w1)):
            w_slice = bars.w1.iloc[: wi + 1]
            bias = weekly_bias(w_slice, n=bias_n)
            if bias == "none":
                continue
            week_start = bars.w1.index[wi]
            week_end = bars.w1.index[wi + 1] if wi + 1 < len(bars.w1) else bars.d1.index[-1]
            d_context_start = max(0, bars.d1.index.get_indexer([week_start], method="nearest")[0] - 10)
            d_context = bars.d1.iloc[d_context_start: bars.d1.index.get_indexer([week_end], method="nearest")[0]]
            sweeps = find_daily_sweeps(d_context, bias, window=len(d_context))
            for sweep in sweeps:
                if not (week_start <= sweep.time < week_end):
                    continue
                atr_val = float(atr_series.loc[atr_series.index <= sweep.time].iloc[-1])
                setup = build_setup(bars.d1, sweep, symbol, min_confluences=min_conf)
                if setup is None:
                    continue
                trade = find_entry(bars.d1, setup, atr_val,
                                   tp3_method=tp3_method, tp3_r_fixed=tp3_r)
                if trade is None:
                    continue
                if all_results and all_results[-1]["symbol"] == symbol and trade.entry_time <= all_results[-1]["exit_time"]:
                    continue
                r = simulate(trade, bars.d1, balance=ACCOUNT, risk_pct=risk_pct, leverage=LEVERAGE)
                if r.exit_reason == "margin_rejected":
                    continue
                all_results.append({"symbol": symbol, "entry_time": r.entry_time,
                                     "exit_time": r.exit_time, "pnl": r.pnl_dollar, "rr": r.rr_realized})

    if not all_results:
        return None
    df = pd.DataFrame(all_results).sort_values("entry_time").reset_index(drop=True)

    # Compound equity
    equity = ACCOUNT
    eq_after = []
    for _, t in df.iterrows():
        equity += t["pnl"] * (equity / ACCOUNT)
        eq_after.append(equity)
    df["equity"] = eq_after

    n_years = (df["entry_time"].max() - df["entry_time"].min()).days / 365.25
    cagr = (equity / ACCOUNT) ** (1 / n_years) - 1
    max_dd = (df["equity"] / df["equity"].cummax() - 1).min() * 100

    return {
        "trades": len(df),
        "winrate%": round((df["pnl"] > 0).mean() * 100, 1),
        "total%": round((equity / ACCOUNT - 1) * 100, 1),
        "CAGR%": round(cagr * 100, 2),
        "maxDD%": round(max_dd, 1),
        "end$": round(equity, 0),
        "calmar": round((cagr * 100) / abs(max_dd), 2) if max_dd != 0 else None,
    }


def main() -> None:
    risk_grid = [1.0, 2.0, 3.0]
    conf_grid = [2, 3]
    tp3_grid = [("swing_30", 0), ("fixed_R", 4.0), ("fixed_R", 6.0)]
    symbol_grid = [
        ("all", list(SYMBOL_MAP.keys())),
        ("no_US2000", [s for s in SYMBOL_MAP if s != "US2000"]),
    ]
    bias_grid = [3, 5]   # 3 closes (loose) vs 5 closes (strict)

    combos = list(itertools.product(risk_grid, conf_grid, tp3_grid, symbol_grid, bias_grid))
    print(f"Running {len(combos)} parameter combinations…\n")

    results = []
    for i, (risk, conf, (tp3_method, tp3_r), (sym_label, syms), bias_n) in enumerate(combos, 1):
        label = f"risk={risk}% conf>={conf} tp3={tp3_method}{'_'+str(tp3_r) if tp3_method=='fixed_R' else ''} {sym_label} bias_n={bias_n}"
        r = run_one(risk, conf, tp3_method, tp3_r, syms, bias_n)
        if r is None:
            continue
        r["config"] = label
        r["risk%"] = risk; r["min_conf"] = conf; r["tp3"] = f"{tp3_method}_{tp3_r}" if tp3_method=="fixed_R" else tp3_method
        r["symbols"] = sym_label; r["bias_n"] = bias_n
        results.append(r)
        print(f"[{i:>2}/{len(combos)}] {label}")
        print(f"        → CAGR {r['CAGR%']:+.2f}%  total {r['total%']:+.1f}%  DD {r['maxDD%']:.1f}%  Calmar {r['calmar']}  trades {r['trades']}")

    df = pd.DataFrame(results)
    df = df.sort_values("CAGR%", ascending=False).reset_index(drop=True)

    print("\n\n" + "=" * 95)
    print("TOP 10 by CAGR (with drawdown — beware of high DD = thin ice)")
    print("=" * 95)
    cols = ["CAGR%", "total%", "maxDD%", "calmar", "trades", "winrate%", "risk%", "min_conf", "tp3", "symbols", "bias_n"]
    print(df[cols].head(10).to_string(index=False))

    print("\n" + "=" * 95)
    print("TOP 10 by CALMAR (return per unit of drawdown — best risk-adjusted)")
    print("=" * 95)
    print(df.sort_values("calmar", ascending=False)[cols].head(10).to_string(index=False))

    out = Path(__file__).parent / "results" / "sweep_results.csv"
    df.to_csv(out, index=False)
    print(f"\nFull table: {out}")


if __name__ == "__main__":
    main()
