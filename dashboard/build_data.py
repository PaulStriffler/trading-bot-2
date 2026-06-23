"""Generate dashboard/data.js with all data embedded.

Primary data source: v3 (FINAL strategy, 2-year 1H backtest).
Also keeps yearly aggregation, equity curve, KPIs and editable bot config.
Embeds everything as `window.DATA = {...}` so the dashboard works on file://.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRADES_CSV = ROOT / "backtest" / "quick" / "results" / "trades_v3_2y.csv"
PNG_REL = "../backtest/quick/results/pngs_v3"
STARTING = 10_000


def main() -> None:
    trades = pd.read_csv(TRADES_CSV, parse_dates=["entry_time", "exit_time"]).sort_values("entry_time").reset_index(drop=True)
    valid = trades[trades["exit_reason"] != "margin_rejected"].copy()
    n = len(valid)
    wins = int((valid["pnl_dollar"] > 0).sum())
    losses = int((valid["pnl_dollar"] < 0).sum())

    # ---- Compound equity walk ----
    equity = STARTING
    eq_curve = []
    scaled_pnls = []
    for _, t in valid.iterrows():
        scaled = float(t["pnl_dollar"]) * (equity / STARTING)
        equity += scaled
        scaled_pnls.append(scaled)
        eq_curve.append({"date": pd.Timestamp(t["exit_time"]).strftime("%Y-%m-%d"), "equity": round(equity, 2)})
    valid["pnl_compound"] = scaled_pnls

    eq_df = pd.DataFrame(eq_curve).groupby("date", as_index=False).last()
    eq_points = eq_df.to_dict("records")

    # ---- Yearly aggregation ----
    valid["year"] = valid["entry_time"].dt.year
    yearly_list = []
    eq_run = STARTING
    for year, grp in valid.groupby("year"):
        start_eq = eq_run
        for _, t in grp.iterrows():
            eq_run += float(t["pnl_dollar"]) * (eq_run / STARTING)
        end_eq = eq_run
        yearly_list.append({
            "year": int(year),
            "trades": int(len(grp)),
            "wins": int((grp["pnl_dollar"] > 0).sum()),
            "equity_start": round(start_eq, 0),
            "equity_end": round(end_eq, 0),
            "pnl_$": round(end_eq - start_eq, 0),
            "return_%": round((end_eq / start_eq - 1) * 100, 1),
        })

    # ---- KPIs ----
    total_pnl = sum(scaled_pnls)
    end_equity = STARTING + total_pnl
    total_return = (end_equity / STARTING - 1) * 100
    n_years = (valid["entry_time"].max() - valid["entry_time"].min()).days / 365.25
    cagr = (end_equity / STARTING) ** (1 / n_years) - 1 if n_years > 0 else 0
    eq_series = pd.Series([p["equity"] for p in eq_points])
    max_dd = ((eq_series / eq_series.cummax() - 1).min() * 100) if not eq_series.empty else 0

    # ---- Last 3 trades ----
    last3 = valid.tail(3).iloc[::-1]
    last3_list = []
    for i, (_, r) in enumerate(last3.iterrows()):
        last3_list.append({
            "n": int(r.name + 1),
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_time": pd.Timestamp(r["entry_time"]).strftime("%Y-%m-%d %H:%M"),
            "exit_time": pd.Timestamp(r["exit_time"]).strftime("%Y-%m-%d %H:%M"),
            "entry": round(float(r["entry_price"]), 2),
            "exit_reason": r["exit_reason"],
            "rr": round(float(r["rr_realized"]), 2),
            "pnl": round(float(r["pnl_dollar"]), 2),
            "confluences": r["confluences"],
        })

    # ---- Full trade journal ----
    trades_list = []
    valid_reset = valid.reset_index(drop=True)
    for i, r in valid_reset.iterrows():
        trades_list.append({
            "n": int(i + 1),
            "symbol": r["symbol"],
            "direction": r["direction"],
            "entry_time": pd.Timestamp(r["entry_time"]).strftime("%Y-%m-%d %H:%M"),
            "exit_time": pd.Timestamp(r["exit_time"]).strftime("%Y-%m-%d %H:%M"),
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
            "png": f"{PNG_REL}/trade-{i+1:03d}.png",
        })

    # ---- Strategies ----
    strategies = [{
        "id": "ict-smc-final-v3",
        "name": "ICT/SMC Multi-TF (v3 FINAL)",
        "status": "active",
        "description": (
            "Vollständige Multi-Timeframe Smart-Money-Strategie: Weekly Bias → Daily Liquidity Sweep → "
            "4H Order Block → 1H Sequenz: Preis verlässt OB → kehrt zurück → FVG bildet sich im OB → "
            "BOS aus der FVG → Entry. 3 Take-Profits (PAL oder Fib-Extension), SL nach TP1 auf BE."
        ),
        "markets": ["US500", "US30", "US100", "US2000"],
        "timeframes": {"bias": "W1", "sweep": "D1", "OB": "H4", "entry": "H1"},
        "rules": [
            "Weekly Bias: letzter BOS oder 5 Closes in Folge",
            "Daily Liquidity Sweep gegen den Bias",
            "Order Block auf 4H markieren (letzter gegensätzlicher Move-Block vor Sweep)",
            "Preis muss aus dem OB rauskommen",
            "Preis muss wieder in den OB reinkommen",
            "Im OB muss eine Confluence (FVG) entstehen",
            "BOS raus aus der FVG bestätigt den Entry",
            "SL: OB-Extrem ± 0.5 × ATR(4H)",
            "TP1 = 1R, TP3 = nächste Daily-PAL oder Fib-Extension, TP2 = Mitte",
        ],
        "trades": n,
        "winrate": round(wins / n * 100, 1) if n else 0,
        "return_total": round(total_return, 2),
        "cagr": round(cagr * 100, 2),
        "max_dd": round(max_dd, 1),
    }, {
        "id": "ict-smc-daytrading",
        "name": "ICT/SMC Daytrading",
        "status": "planned",
        "description": "Geplant: Daytrading-Variante mit Killzone-Filter (London/NY Open), 15min Entries, intraday Risk-Off vor Close.",
        "markets": ["US500", "US30", "US100", "US2000"],
        "timeframes": {"bias": "H4", "sweep": "H1", "confluence": "M15", "entry": "M5"},
        "rules": ["Wird nach v3 Live-Validierung erarbeitet"],
    }]

    # ---- Bots ----
    bots = [{
        "id": "bot-v3-final",
        "name": "ICT/SMC FINAL Bot v3",
        "strategy_id": "ict-smc-final-v3",
        "status": "backtest_only",
        "description": "Aktueller v3-Bot, läuft als 2-Jahres-Backtest auf yfinance 1H. Live-Anbindung an FTMO/MT5 in der nächsten Phase.",
        "params": {
            "account_usd": 10000,
            "leverage": 30,
            "risk_per_trade_pct": 1.0,
            "sl_atr_buffer": 0.5,
            "atr_period": 14,
            "tp1_rr": 1.0,
            "tp3_method": "PAL_or_FibExt",
            "max_wait_bars_1h": 80,
            "partial_close_pct": [0.33, 0.33, 0.34],
            "move_sl_to_be_at_tp1": True,
            "kill_switch_daily_loss_pct": 3.0,
        },
        "performance": {
            "trades": n,
            "winrate": round(wins / n * 100, 1) if n else 0,
            "wins": wins,
            "losses": losses,
            "total_return_pct": round(total_return, 2),
            "max_dd_pct": round(max_dd, 1),
            "cagr_pct": round(cagr * 100, 2),
            "end_equity": round(end_equity, 2),
        }
    }]

    data = {
        "kpis": {
            "trades": n,
            "wins": wins,
            "losses": losses,
            "winrate": round(wins / n * 100, 1) if n else 0,
            "total_return_pct": round(total_return, 2),
            "cagr_pct": round(cagr * 100, 2),
            "max_dd_pct": round(max_dd, 1),
            "end_equity": round(end_equity, 2),
            "starting_equity": STARTING,
            "data_period_start": pd.Timestamp(valid["entry_time"].min()).strftime("%Y-%m-%d"),
            "data_period_end": pd.Timestamp(valid["entry_time"].max()).strftime("%Y-%m-%d"),
            "data_years": round(n_years, 2),
            "n_symbols": int(len(valid["symbol"].unique())),
            "symbols": sorted(list(valid["symbol"].unique())),
            "strategy_version": "v3 FINAL",
            "timeframe_entry": "1H",
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
    print(f"  {n} trades, winrate {wins/n*100:.1f}%, total {total_return:+.2f}%, CAGR {cagr*100:.2f}%, MaxDD {max_dd:.1f}%")


if __name__ == "__main__":
    main()
