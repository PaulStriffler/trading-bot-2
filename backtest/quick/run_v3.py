"""2-Year v3 backtest — real multi-timeframe on 1H data from yfinance."""
from __future__ import annotations

import pickle
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch
from .engine import simulate
from .strategy import atr, find_daily_sweeps
from .strategy_v3 import find_entry_v3, find_ob_4h, weekly_bias_v3

warnings.filterwarnings("ignore")

ACCOUNT = 10_000
RISK_PCT = 1.0
LEVERAGE = 30.0
WEEKS = 100  # ~700 days — yfinance 1H limit is 730 days, leave a small buffer


def fetch_2y(symbol):
    """Re-fetch with extended window — pad enough history for bias on Weekly."""
    from .data import _normalize, _resample_4h
    import yfinance as yf
    ticker = SYMBOL_MAP[symbol]
    end = datetime.utcnow()
    start_long = end - timedelta(weeks=WEEKS + 30)
    start_1h = end - timedelta(days=720)  # within 730-day yfinance cap
    w1 = _normalize(yf.download(ticker, start=start_long, end=end, interval="1wk", progress=False, auto_adjust=False))
    d1 = _normalize(yf.download(ticker, start=start_long, end=end, interval="1d", progress=False, auto_adjust=False))
    h1 = _normalize(yf.download(ticker, start=start_1h, end=end, interval="1h", progress=False, auto_adjust=False))
    h4 = _resample_4h(h1)
    class B: pass
    b = B(); b.symbol = symbol; b.h1 = h1; b.h4 = h4; b.d1 = d1; b.w1 = w1
    return b


def run():
    all_results = []
    all_annotations: dict[str, "V3Annotations"] = {}
    diag = {"bias_none": 0, "no_sweep_in_week": 0, "no_ob": 0, "no_entry": 0}

    for symbol in SYMBOL_MAP:
        print(f"\n=== {symbol} ===")
        bars = fetch_2y(symbol)
        if bars.h1.empty:
            print("  no 1H data")
            continue
        atr_4h_series = atr(bars.h4, period=14)

        trades_in_symbol = 0
        for wi in range(8, len(bars.w1)):
            w_slice = bars.w1.iloc[: wi + 1]
            bias = weekly_bias_v3(w_slice)
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
                ob = find_ob_4h(bars.h4, sweep)
                if ob is None:
                    diag["no_ob"] += 1
                    continue
                ob_low, ob_high, ob_time = ob

                # ATR(4H) at the time of sweep
                atr_idx = atr_4h_series.index.get_indexer([sweep.time], method="nearest")[0]
                atr_4h_val = float(atr_4h_series.iloc[atr_idx])

                res = find_entry_v3(bars.h1, bars.d1, sweep, symbol,
                                     ob_low, ob_high, ob_time, atr_4h_val)
                if res is None:
                    diag["no_entry"] += 1
                    continue
                trade, ann = res

                # Don't overlap with last open trade in this symbol
                if all_results and all_results[-1].symbol == symbol and trade.entry_time <= all_results[-1].exit_time:
                    continue
                result = simulate(trade, bars.h1, balance=ACCOUNT, risk_pct=RISK_PCT, leverage=LEVERAGE)
                if result.exit_reason == "margin_rejected":
                    continue
                key = f"{symbol}_{trade.entry_time.strftime('%Y%m%d_%H%M')}"
                all_annotations[key] = ann
                all_results.append(result)
                trades_in_symbol += 1
        print(f"  trades: {trades_in_symbol}")

    # ---- Summary ----
    print("\n" + "=" * 70)
    print(f"v3 SUMMARY · 2-Year Multi-TF Backtest · 1H Entries (yfinance)")
    print("=" * 70)
    print(f"Account: ${ACCOUNT:,}  Risk: {RISK_PCT}%  Leverage: 1:{int(LEVERAGE)}")
    print(f"Total trades: {len(all_results)}")
    print(f"Diagnostics: bias-none={diag['bias_none']}, no-sweep={diag['no_sweep_in_week']}, "
          f"no-ob={diag['no_ob']}, no-entry={diag['no_entry']}")

    if not all_results:
        print("→ No trades passed v3.")
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
    n_years = (df["entry_time"].max() - df["entry_time"].min()).days / 365.25
    cagr = (equity / ACCOUNT) ** (1 / n_years) - 1 if n_years > 0 else 0
    max_dd = (df["equity"] / df["equity"].cummax() - 1).min() * 100

    print(f"Winrate: {winrate:.1f}%   Total R: {total_r:+.2f}")
    print(f"Total Return (compound): {(equity/ACCOUNT-1)*100:+.2f}%   End equity: ${equity:,.2f}")
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
    df.drop(columns=["year"]).to_csv(out / "trades_v3_2y.csv", index=False)
    # Pickle annotations so the screenshot pass can draw boxes
    with open(out / "annotations_v3.pkl", "wb") as f:
        pickle.dump(all_annotations, f)
    print(f"\nSaved: trades_v3_2y.csv, annotations_v3.pkl")


if __name__ == "__main__":
    run()
