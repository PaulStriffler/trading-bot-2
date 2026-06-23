"""Build an HTML viewer with all 9 POC trades on 4H charts.

Uses TradingView's open-source Lightweight Charts library via CDN.
Each trade gets its own panel with candles, entry/SL/TP lines and a
deep-link to the corresponding symbol on TradingView.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd

from .data import SYMBOL_MAP, fetch

warnings.filterwarnings("ignore")

# Symbols TradingView uses for the spot indices (free, no broker login needed).
TV_SYMBOL: dict[str, str] = {
    "US500": "TVC:SPX",
    "US30": "TVC:DJI",
    "US100": "TVC:NDQ",
    "US2000": "TVC:RUT",
}


def _bars_for_trade(h4: pd.DataFrame, entry_time: pd.Timestamp, exit_time: pd.Timestamp,
                    pad_bars: int = 24) -> pd.DataFrame:
    idx_in = h4.index.get_indexer([entry_time], method="nearest")[0]
    idx_out = h4.index.get_indexer([exit_time], method="nearest")[0]
    lo = max(0, idx_in - pad_bars)
    hi = min(len(h4), idx_out + pad_bars)
    return h4.iloc[lo:hi]


def _candles_json(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "time": int(ts.timestamp()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        }
        for ts, row in df.iterrows()
    ]


def build_viewer(trades_csv: Path, out_html: Path) -> Path:
    trades = pd.read_csv(trades_csv, parse_dates=["entry_time", "exit_time"])

    # Cache 4H bars per symbol (one fetch each)
    h4_by_sym: dict[str, pd.DataFrame] = {}
    for sym in trades["symbol"].unique():
        h4_by_sym[sym] = fetch(sym, weeks=3).h4

    panels = []
    for i, t in trades.iterrows():
        sym = t["symbol"]
        h4 = h4_by_sym[sym]
        slice_ = _bars_for_trade(h4, t["entry_time"], t["exit_time"])
        if slice_.empty:
            continue
        candles = _candles_json(slice_)
        panels.append({
            "id": f"chart-{i}",
            "title": f"#{i+1} · {sym} · {t['direction'].upper()} · {t['exit_reason']} · "
                     f"R={t['rr_realized']:.2f} · ${t['pnl_dollar']:+.0f}",
            "subtitle": f"{t['confluences']} · entry {t['entry_time']:%Y-%m-%d %H:%M} → exit {t['exit_time']:%Y-%m-%d %H:%M}",
            "symbol": sym,
            "tv_symbol": TV_SYMBOL[sym],
            "candles": candles,
            "entry_time": int(t["entry_time"].timestamp()),
            "exit_time": int(t["exit_time"].timestamp()),
            "entry": float(t["entry_price"]),
            "sl": float(t["sl"]),
            "tp1": float(t["tp1"]),
            "tp2": float(t["tp2"]),
            "tp3": float(t["tp3"]),
            "win": float(t["pnl_dollar"]) > 0,
        })

    html = _render(panels)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html


def _render(panels: list[dict]) -> str:
    panels_json = json.dumps(panels)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Trading-Bot POC · 9 Trades · 4H</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
  body {{ background:#0e1116; color:#d7dae0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; margin:0; padding:24px; }}
  h1 {{ margin:0 0 8px; font-weight:600; }}
  .sub {{ color:#888; margin-bottom:32px; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(560px,1fr)); gap:24px; }}
  .card {{ background:#181b22; border:1px solid #262a33; border-radius:8px; overflow:hidden; }}
  .card-head {{ padding:12px 16px; border-bottom:1px solid #262a33; display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }}
  .card-title {{ font-weight:600; font-size:14px; }}
  .card-title.win {{ color:#26a69a; }}
  .card-title.loss {{ color:#ef5350; }}
  .card-sub {{ color:#888; font-size:12px; margin-top:2px; }}
  .tv-link {{ background:#2962ff; color:white; text-decoration:none; padding:6px 12px; border-radius:4px; font-size:12px; white-space:nowrap; }}
  .tv-link:hover {{ background:#1e4dd9; }}
  .chart {{ height:340px; }}
  .legend {{ padding:8px 16px; border-top:1px solid #262a33; font-size:11px; display:flex; gap:16px; flex-wrap:wrap; color:#aaa; }}
  .legend span::before {{ content:""; display:inline-block; width:10px; height:2px; vertical-align:middle; margin-right:6px; }}
  .l-entry::before {{ background:#ffffff; }}
  .l-sl::before {{ background:#ef5350; }}
  .l-tp1::before {{ background:#26a69a; }}
  .l-tp2::before {{ background:#42b48a; }}
  .l-tp3::before {{ background:#66bb6a; }}
</style>
</head>
<body>
<h1>Trading-Bot POC · 9 Trades · 4H Charts</h1>
<p class="sub">ICT/SMC Quick-Backtest auf US500/30/100/2000 · Account $10.000 · 1 % Risk · Daten via yfinance</p>
<div class="grid" id="grid"></div>
<script>
const panels = {panels_json};
const grid = document.getElementById("grid");

panels.forEach(p => {{
  const card = document.createElement("div"); card.className = "card";
  const head = document.createElement("div"); head.className = "card-head";
  const titleWrap = document.createElement("div");
  const title = document.createElement("div");
  title.className = "card-title " + (p.win ? "win" : "loss");
  title.textContent = p.title;
  const sub = document.createElement("div");
  sub.className = "card-sub";
  sub.textContent = p.subtitle;
  titleWrap.appendChild(title); titleWrap.appendChild(sub);
  const link = document.createElement("a");
  link.className = "tv-link";
  link.href = `https://www.tradingview.com/chart/?symbol=${{p.tv_symbol}}&interval=240`;
  link.target = "_blank";
  link.textContent = "TradingView →";
  head.appendChild(titleWrap); head.appendChild(link);

  const chartEl = document.createElement("div"); chartEl.className = "chart"; chartEl.id = p.id;

  const legend = document.createElement("div"); legend.className = "legend";
  legend.innerHTML = '<span class="l-entry">Entry ' + p.entry.toFixed(1) +
                     '</span><span class="l-sl">SL ' + p.sl.toFixed(1) +
                     '</span><span class="l-tp1">TP1 ' + p.tp1.toFixed(1) +
                     '</span><span class="l-tp2">TP2 ' + p.tp2.toFixed(1) +
                     '</span><span class="l-tp3">TP3 ' + p.tp3.toFixed(1) + '</span>';

  card.appendChild(head); card.appendChild(chartEl); card.appendChild(legend);
  grid.appendChild(card);

  const chart = LightweightCharts.createChart(chartEl, {{
    layout: {{ background: {{ color:"#181b22" }}, textColor:"#aaa" }},
    grid: {{ vertLines: {{ color:"#222" }}, horzLines: {{ color:"#222" }} }},
    rightPriceScale: {{ borderColor:"#333" }},
    timeScale: {{ borderColor:"#333", timeVisible:true, secondsVisible:false }},
  }});
  const series = chart.addCandlestickSeries({{
    upColor:"#26a69a", downColor:"#ef5350", borderVisible:false,
    wickUpColor:"#26a69a", wickDownColor:"#ef5350",
  }});
  series.setData(p.candles);

  const line = (price, color, title) => series.createPriceLine({{
    price, color, lineWidth:1, lineStyle:LightweightCharts.LineStyle.Dashed, title,
  }});
  line(p.entry, "#ffffff", "Entry");
  line(p.sl, "#ef5350", "SL");
  line(p.tp1, "#26a69a", "TP1");
  line(p.tp2, "#42b48a", "TP2");
  line(p.tp3, "#66bb6a", "TP3");

  series.setMarkers([
    {{ time:p.entry_time, position:"belowBar", color:"#2962ff", shape:"arrowUp", text:"ENTRY" }},
    {{ time:p.exit_time, position:"aboveBar", color:p.win?"#26a69a":"#ef5350",
       shape:"arrowDown", text:"EXIT" }},
  ]);
  chart.timeScale().fitContent();
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    root = Path(__file__).parent
    csv = root / "results" / "trades.csv"
    out = root / "results" / "trades.html"
    path = build_viewer(csv, out)
    print(f"Wrote: {path}")
    print(f"Open: file://{path}")
