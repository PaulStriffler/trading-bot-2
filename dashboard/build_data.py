"""Generate dashboard/data.js with all data embedded.

Reads from backtest/quick/results/*.csv and configs/strategy.yaml,
then writes a single JS file `const DATA = {...}` that the dashboard's
index.html loads via <script src>. Embedding keeps the dashboard a
self-contained local file (no CORS issues from fetch() on file://).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRADES_CSV = ROOT / "backtest" / "quick" / "results" / "trades_8y.csv"
YEARLY_CSV = ROOT / "backtest" / "quick" / "results" / "yearly_compounded.csv"
STARTING = 10_000


def main() -> None:
    trades = pd.read_csv(TRADES_CSV, parse_dates=["entry_time", "exit_time"]).sort_values("entry_time").reset_index(drop=True)
    yearly = pd.read_csv(YEARLY_CSV)

    # ---- KPIs ----
    valid = trades[trades["exit_reason"] != "margin_rejected"]
    wins = int((valid["pnl_dollar"] > 0).sum())
    losses = int((valid["pnl_dollar"] < 0).sum())
    n = int(len(valid))

    # Compound equity walk
    equity, equity_curve, scaled_pnls = STARTING, [], []
    for _, t in trades.iterrows():
        scaled = float(t["pnl_dollar"]) * (equity / STARTING)
        equity += scaled
        scaled_pnls.append(scaled)
        equity_curve.append({
            "date": pd.Timestamp(t["exit_time"]).strftime("%Y-%m-%d"),
            "equity": round(equity, 2),
        })
    trades["pnl_compound"] = scaled_pnls

    # Equity curve aggregated per day (last value of day wins)
    eq_df = pd.DataFrame(equity_curve).groupby("date", as_index=False).last()
    eq_points = eq_df.to_dict("records")

    # ---- Last 3 trades ----
    last3 = valid.tail(3).iloc[::-1]  # most recent first
    last3_list = [{
        "n": int(i + 1),
        "symbol": r["symbol"],
        "direction": r["direction"],
        "entry_time": pd.Timestamp(r["entry_time"]).strftime("%Y-%m-%d"),
        "exit_time": pd.Timestamp(r["exit_time"]).strftime("%Y-%m-%d"),
        "entry": round(float(r["entry_price"]), 2),
        "exit_reason": r["exit_reason"],
        "rr": round(float(r["rr_realized"]), 2),
        "pnl": round(float(r["pnl_dollar"]), 2),
        "confluences": r["confluences"],
    } for i, (_, r) in enumerate(last3.iterrows())]

    # ---- Full trade journal ----
    trades_list = []
    for i, r in valid.iterrows():
        trades_list.append({
            "n": int(i + 1),
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_time": pd.Timestamp(r["entry_time"]).strftime("%Y-%m-%d"),
            "exit_time": pd.Timestamp(r["exit_time"]).strftime("%Y-%m-%d"),
            "entry": round(float(r["entry_price"]), 2),
            "sl": round(float(r["sl"]), 2),
            "tp1": round(float(r["tp1"]), 2),
            "tp2": round(float(r["tp2"]), 2),
            "tp3": round(float(r["tp3"]), 2),
            "exit_reason": r["exit_reason"],
            "rr": round(float(r["rr_realized"]), 2),
            "pnl": round(float(r["pnl_dollar"]), 2),
            "confluences": r["confluences"],
            "leverage_used": round(float(r.get("leverage_used", 0)), 2),
            "margin": round(float(r.get("margin_required", 0)), 2),
            "png": f"../backtest/quick/results/pngs_8y/trade-{i+1:03d}.png",
        })

    # ---- Yearly ----
    yearly_list = yearly.to_dict("records")
    for y in yearly_list:
        y["return_%"] = float(y["return_%"])
        y["trades"] = int(y["trades"])
        y["equity_start"] = int(y["equity_start"])
        y["equity_end"] = int(y["equity_end"])

    data_period_start = pd.Timestamp(trades["entry_time"].min()).strftime("%Y-%m-%d")
    data_period_end = pd.Timestamp(trades["entry_time"].max()).strftime("%Y-%m-%d")
    n_years = (trades["entry_time"].max() - trades["entry_time"].min()).days / 365.25
    cagr = (equity / STARTING) ** (1 / n_years) - 1

    # Max DD
    eq_series = pd.Series([p["equity"] for p in eq_points])
    rolling_max = eq_series.cummax()
    max_dd = ((eq_series / rolling_max - 1).min() * 100)

    # ---- Strategies metadata ----
    strategies = [{
        "id": "ict-smc-swing",
        "name": "ICT/SMC Swing",
        "status": "active",
        "description": "Multi-Timeframe Smart-Money-Strategie: Weekly Bias → Daily Liquidity Sweep → 4H Confluences → 1H Entry. Drei Take-Profits, SL nach TP1 auf Break-even.",
        "markets": ["US500", "US30", "US100", "US2000"],
        "timeframes": {"bias": "W1", "sweep": "D1", "confluence": "H4", "entry": "H1"},
        "rules": [
            "Weekly Bias: BOS oder 5 Closes in Folge",
            "Daily Liquidity Sweep gegen den Bias",
            "Min. 2 von 4 Confluences (OB, FVG, BPR, Equilibrium) — 1 davon BOS",
            "Entry bei 1H BOS nach OB-Tap",
            "SL: Sweep-Extrem ± 0.5 × ATR(4H)",
            "TPs: 1:1 RR / Mid / Daily Liquidity",
        ],
        "trades": n,
        "winrate": round(wins / n * 100, 1) if n else 0,
        "return_total": round((equity - STARTING) / STARTING * 100, 2),
        "cagr": round(cagr * 100, 2),
        "max_dd": round(max_dd, 1),
    }, {
        "id": "ict-smc-daytrading",
        "name": "ICT/SMC Daytrading",
        "status": "planned",
        "description": "Geplant: Daytrading-Variante mit Killzone-Filter (London/NY Open), 15min Entries, intraday Risk-Off vor Close.",
        "markets": ["US500", "US30", "US100", "US2000"],
        "timeframes": {"bias": "H4", "sweep": "H1", "confluence": "M15", "entry": "M5"},
        "rules": ["Wird in Phase 6 erarbeitet"],
    }]

    # ---- Bots ----
    bots = [{
        "id": "bot-poc-1",
        "name": "ICT/SMC Swing Bot v1 (POC)",
        "strategy_id": "ict-smc-swing",
        "status": "backtest_only",
        "description": "POC-Bot, läuft als Backtest auf yfinance-Daten. Live-Anbindung an MT5 in Phase 8.",
        "params": {
            "account_eur": 10000,
            "leverage": 30,
            "risk_per_trade_pct": 1.0,
            "min_confluences": 2,
            "sl_atr_buffer": 0.5,
            "atr_period": 14,
            "tp1_rr": 1.0,
            "partial_close_pct": [0.33, 0.33, 0.34],
            "move_sl_to_be_at_tp1": True,
            "kill_switch_daily_loss_pct": 3.0,
        },
        "performance": {
            "trades": n,
            "winrate": round(wins / n * 100, 1) if n else 0,
            "wins": wins,
            "losses": losses,
            "total_return_pct": round((equity - STARTING) / STARTING * 100, 2),
            "max_dd_pct": round(max_dd, 1),
            "cagr_pct": round(cagr * 100, 2),
            "end_equity": round(equity, 2),
        }
    }]

    data = {
        "kpis": {
            "trades": n,
            "wins": wins,
            "losses": losses,
            "winrate": round(wins / n * 100, 1) if n else 0,
            "total_return_pct": round((equity - STARTING) / STARTING * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "max_dd_pct": round(max_dd, 1),
            "end_equity": round(equity, 2),
            "starting_equity": STARTING,
            "data_period_start": data_period_start,
            "data_period_end": data_period_end,
            "data_years": round(n_years, 1),
            "n_symbols": len(trades["symbol"].unique()),
            "symbols": sorted(list(trades["symbol"].unique())),
        },
        "equity_curve": eq_points,
        "yearly": yearly_list,
        "last3": last3_list,
        "trades": trades_list,
        "strategies": strategies,
        "bots": bots,
    }

    out = Path(__file__).parent / "data.js"
    out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
                   encoding="utf-8")
    print(f"Wrote {out}  ({out.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
