"""HTML viewer + PNGs for the 8-year backtest.

Daily-variant strategy → candles rendered are Daily bars. Adds an
equity-curve panel at the top before the per-trade cards.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch_long
from .screenshots import TV_SYMBOL, _candles_json

warnings.filterwarnings("ignore")


def _bars_for_trade(d1: pd.DataFrame, entry_time: pd.Timestamp, exit_time: pd.Timestamp,
                    pad_bars: int = 40) -> pd.DataFrame:
    idx_in = d1.index.get_indexer([entry_time], method="nearest")[0]
    idx_out = d1.index.get_indexer([exit_time], method="nearest")[0]
    lo = max(0, idx_in - pad_bars)
    hi = min(len(d1), idx_out + pad_bars)
    return d1.iloc[lo:hi]


def build(trades_csv: Path, out_html: Path) -> Path:
    trades = pd.read_csv(trades_csv, parse_dates=["entry_time", "exit_time"])
    trades = trades.sort_values("entry_time").reset_index(drop=True)

    d1_by_sym: dict[str, pd.DataFrame] = {}
    for sym in trades["symbol"].unique():
        d1_by_sym[sym] = fetch_long(sym, years=8).d1

    # Equity curve data — aggregate to one point per calendar day
    # (Lightweight Charts area series rejects duplicate time values silently)
    starting = 10_000
    eq_df = trades[["exit_time", "pnl_dollar"]].copy()
    eq_df["day"] = eq_df["exit_time"].dt.normalize()
    daily_pnl = eq_df.groupby("day")["pnl_dollar"].sum().sort_index()
    daily_equity = starting + daily_pnl.cumsum()
    equity_points = [{"time": d.strftime("%Y-%m-%d"), "value": float(eq)}
                     for d, eq in daily_equity.items()]
    first_day = (trades["entry_time"].min().normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    equity_points.insert(0, {"time": first_day, "value": float(starting)})

    # Yearly bars
    yearly_df = trades.assign(year=trades["entry_time"].dt.year).groupby("year").agg(
        pnl=("pnl_dollar", "sum"),
        trades=("year", "count"),
        wins=("pnl_dollar", lambda s: (s > 0).sum()),
    )
    yearly_df["pct"] = yearly_df["pnl"] / starting * 100
    yearly = [
        {"year": int(y), "pnl": float(r.pnl), "pct": float(r.pct),
         "trades": int(r.trades), "wins": int(r.wins)}
        for y, r in yearly_df.iterrows()
    ]

    panels = []
    for i, t in trades.iterrows():
        sym = t["symbol"]
        d1 = d1_by_sym[sym]
        slc = _bars_for_trade(d1, t["entry_time"], t["exit_time"])
        if slc.empty:
            continue
        panels.append({
            "id": f"chart-{i}",
            "n": i + 1,
            "title": f"#{i+1} · {sym} · {t['direction'].upper()} · {t['exit_reason']} · "
                     f"R={t['rr_realized']:+.2f} · ${t['pnl_dollar']:+.0f}",
            "subtitle": f"{t['confluences']} · {t['entry_time']:%Y-%m-%d} → {t['exit_time']:%Y-%m-%d}",
            "tv_symbol": TV_SYMBOL[sym],
            "candles": _candles_json(slc),
            "entry_time": int(t["entry_time"].timestamp()),
            "exit_time": int(t["exit_time"].timestamp()),
            "entry": float(t["entry_price"]),
            "sl": float(t["sl"]),
            "tp1": float(t["tp1"]),
            "tp2": float(t["tp2"]),
            "tp3": float(t["tp3"]),
            "win": float(t["pnl_dollar"]) > 0,
        })

    html = _render(panels, equity_points, yearly,
                   total_pnl=float(trades["pnl_dollar"].sum()),
                   winrate=float((trades["pnl_dollar"] > 0).mean() * 100),
                   total_r=float(trades["rr_realized"].sum()),
                   n_trades=len(trades))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html


def _render(panels, equity_points, yearly, *, total_pnl, winrate, total_r, n_trades) -> str:
    pj, eqj, yj = json.dumps(panels), json.dumps(equity_points), json.dumps(yearly)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Trading-Bot 8-Year Backtest · {n_trades} Trades</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
  body {{ background:#0e1116; color:#d7dae0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; margin:0; padding:24px; }}
  h1 {{ margin:0 0 4px; font-weight:600; }}
  .sub {{ color:#888; margin-bottom:24px; font-size:14px; }}
  .kpis {{ display:flex; gap:24px; flex-wrap:wrap; margin-bottom:24px; }}
  .kpi {{ background:#181b22; border:1px solid #262a33; border-radius:8px; padding:16px 24px; min-width:140px; }}
  .kpi-label {{ color:#888; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; }}
  .kpi-value {{ font-size:22px; font-weight:600; margin-top:4px; }}
  .kpi-value.win {{ color:#26a69a; }}
  .kpi-value.loss {{ color:#ef5350; }}
  .panel {{ background:#181b22; border:1px solid #262a33; border-radius:8px; padding:16px; margin-bottom:24px; }}
  .panel h2 {{ margin:0 0 12px; font-size:14px; color:#aaa; font-weight:500; }}
  #equity {{ height:280px; }}
  #yearly {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; }}
  .yr {{ background:#1f242d; border-radius:6px; padding:12px; }}
  .yr-y {{ font-size:11px; color:#888; }}
  .yr-pct {{ font-size:18px; font-weight:600; margin-top:4px; }}
  .yr-pct.win {{ color:#26a69a; }}
  .yr-pct.loss {{ color:#ef5350; }}
  .yr-meta {{ font-size:11px; color:#888; margin-top:2px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(560px,1fr)); gap:24px; }}
  .card {{ background:#181b22; border:1px solid #262a33; border-radius:8px; overflow:hidden; }}
  .card-head {{ padding:12px 16px; border-bottom:1px solid #262a33; display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }}
  .card-title {{ font-weight:600; font-size:13px; }}
  .card-title.win {{ color:#26a69a; }}
  .card-title.loss {{ color:#ef5350; }}
  .card-sub {{ color:#888; font-size:11px; margin-top:2px; }}
  .tv-link {{ background:#2962ff; color:white; text-decoration:none; padding:6px 12px; border-radius:4px; font-size:11px; white-space:nowrap; }}
  .chart {{ height:320px; }}
  .legend {{ padding:8px 16px; border-top:1px solid #262a33; font-size:11px; display:flex; gap:14px; flex-wrap:wrap; color:#aaa; }}
  .legend span::before {{ content:""; display:inline-block; width:10px; height:2px; vertical-align:middle; margin-right:6px; }}
  .l-entry::before {{ background:#fff; }}
  .l-sl::before {{ background:#ef5350; }}
  .l-tp1::before {{ background:#26a69a; }}
  .l-tp2::before {{ background:#42b48a; }}
  .l-tp3::before {{ background:#66bb6a; }}
</style>
</head>
<body>
<h1>Trading-Bot · 8-Jahres Backtest (Daily Variant)</h1>
<p class="sub">US500 · US30 · US100 · US2000 · Account $10.000 · 1 % Risk · 3 TPs · Daten via yfinance</p>

<div class="kpis">
  <div class="kpi"><div class="kpi-label">Trades</div><div class="kpi-value">{n_trades}</div></div>
  <div class="kpi"><div class="kpi-label">Winrate</div><div class="kpi-value">{winrate:.1f}%</div></div>
  <div class="kpi"><div class="kpi-label">Total R</div><div class="kpi-value {'win' if total_r > 0 else 'loss'}">{total_r:+.1f}</div></div>
  <div class="kpi"><div class="kpi-label">Total P&L</div><div class="kpi-value {'win' if total_pnl > 0 else 'loss'}">${total_pnl:+,.0f}</div></div>
  <div class="kpi"><div class="kpi-label">End Equity</div><div class="kpi-value">${10000 + total_pnl:,.0f}</div></div>
</div>

<div class="panel"><h2>Equity Curve</h2><div id="equity"></div></div>
<div class="panel"><h2>Performance pro Jahr</h2><div id="yearly"></div></div>

<h2 style="margin:32px 0 16px; font-size:16px;">Alle {n_trades} Trades — chronologisch</h2>
<div class="grid" id="grid"></div>

<script>
const panels = {pj};
const equity = {eqj};
const yearly = {yj};

// --- Equity curve ---
const eqEl = document.getElementById("equity");
const eqChart = LightweightCharts.createChart(eqEl, {{
  layout: {{ background: {{ color:"#181b22" }}, textColor:"#aaa" }},
  grid: {{ vertLines: {{ color:"#222" }}, horzLines: {{ color:"#222" }} }},
  rightPriceScale: {{ borderColor:"#333" }},
  timeScale: {{ borderColor:"#333", timeVisible:false, fixLeftEdge:true, fixRightEdge:true }},
}});
const eqSeries = eqChart.addAreaSeries({{ lineColor:"#26a69a", lineWidth:2, topColor:"rgba(38,166,154,0.45)", bottomColor:"rgba(38,166,154,0.05)" }});
eqSeries.setData(equity);
eqChart.timeScale().fitContent();

// --- Yearly cards ---
const yearlyEl = document.getElementById("yearly");
yearly.forEach(y => {{
  const div = document.createElement("div"); div.className = "yr";
  div.innerHTML = '<div class="yr-y">' + y.year + '</div>' +
    '<div class="yr-pct ' + (y.pct >= 0 ? 'win' : 'loss') + '">' + (y.pct >= 0 ? '+' : '') + y.pct.toFixed(1) + '%</div>' +
    '<div class="yr-meta">' + y.trades + ' trades · ' + Math.round(y.wins / y.trades * 100) + '% wr</div>';
  yearlyEl.appendChild(div);
}});

// --- Per-trade cards ---
const grid = document.getElementById("grid");
panels.forEach(p => {{
  const card = document.createElement("div"); card.className = "card";
  const head = document.createElement("div"); head.className = "card-head";
  const tw = document.createElement("div");
  const t = document.createElement("div"); t.className = "card-title " + (p.win ? "win" : "loss"); t.textContent = p.title;
  const s = document.createElement("div"); s.className = "card-sub"; s.textContent = p.subtitle;
  tw.appendChild(t); tw.appendChild(s);
  const a = document.createElement("a"); a.className = "tv-link"; a.target = "_blank";
  a.href = `https://www.tradingview.com/chart/?symbol=${{p.tv_symbol}}&interval=D`;
  a.textContent = "TradingView →";
  head.appendChild(tw); head.appendChild(a);
  const ce = document.createElement("div"); ce.className = "chart"; ce.id = p.id;
  const leg = document.createElement("div"); leg.className = "legend";
  leg.innerHTML = '<span class="l-entry">Entry ' + p.entry.toFixed(1) + '</span>' +
                  '<span class="l-sl">SL ' + p.sl.toFixed(1) + '</span>' +
                  '<span class="l-tp1">TP1 ' + p.tp1.toFixed(1) + '</span>' +
                  '<span class="l-tp2">TP2 ' + p.tp2.toFixed(1) + '</span>' +
                  '<span class="l-tp3">TP3 ' + p.tp3.toFixed(1) + '</span>';
  card.appendChild(head); card.appendChild(ce); card.appendChild(leg);
  grid.appendChild(card);

  const chart = LightweightCharts.createChart(ce, {{
    layout: {{ background: {{ color:"#181b22" }}, textColor:"#aaa" }},
    grid: {{ vertLines: {{ color:"#222" }}, horzLines: {{ color:"#222" }} }},
    rightPriceScale: {{ borderColor:"#333" }},
    timeScale: {{ borderColor:"#333", timeVisible:false }},
  }});
  const series = chart.addCandlestickSeries({{
    upColor:"#26a69a", downColor:"#ef5350", borderVisible:false,
    wickUpColor:"#26a69a", wickDownColor:"#ef5350",
  }});
  series.setData(p.candles);
  const line = (price, color, title) => series.createPriceLine({{
    price, color, lineWidth:1, lineStyle:LightweightCharts.LineStyle.Dashed, title,
  }});
  line(p.entry, "#fff", "Entry");
  line(p.sl, "#ef5350", "SL");
  line(p.tp1, "#26a69a", "TP1");
  line(p.tp2, "#42b48a", "TP2");
  line(p.tp3, "#66bb6a", "TP3");
  series.setMarkers([
    {{ time:p.entry_time, position:"belowBar", color:"#2962ff", shape:"arrowUp", text:"ENTRY" }},
    {{ time:p.exit_time, position:"aboveBar", color:p.win?"#26a69a":"#ef5350", shape:"arrowDown", text:"EXIT" }},
  ]);
  chart.timeScale().fitContent();
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    root = Path(__file__).parent / "results"
    out = build(root / "trades_8y.csv", root / "trades_8y.html")
    print(f"Wrote: {out}")
