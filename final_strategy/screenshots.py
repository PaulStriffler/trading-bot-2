"""TradingView-style 1H screenshots for v3 trades.

For each trade: 1H candlesticks around the trade, with the OB zone,
FVG zone, Long/Short position rectangle (entry→TP1 green, entry→SL red),
horizontal lines for Entry/SL/TP1/TP2/TP3, and markers for sweep/leave/
re-enter/BOS. Output: 1280×720 PNG.
"""
from __future__ import annotations

import pickle
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from matplotlib.lines import Line2D

from .data import SYMBOL_MAP, _normalize, _resample_4h

warnings.filterwarnings("ignore")
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9})


# --- TradingView color palette ---
COLOR_BG = "#0D1117"
COLOR_PANEL = "#161B22"
COLOR_GRID = "#1F2630"
COLOR_TEXT = "#D7DAE0"
COLOR_TEXT_DIM = "#7E8590"
COLOR_TEXT_FAINT = "#4F5663"
COLOR_UP = "#26A69A"
COLOR_DOWN = "#EF5350"
COLOR_OB = "#2962FF"
COLOR_FVG = "#FF9800"
COLOR_LONG_BOX = "#26A69A"
COLOR_SHORT_BOX = "#EF5350"
COLOR_LOSS_BOX = "#EF5350"


def fetch_1h_for_trade(symbol: str, entry_time, exit_time, pad_before=72, pad_after=24):
    """Fetch a slim window of 1H bars around the trade."""
    ticker = SYMBOL_MAP[symbol]
    start = pd.Timestamp(entry_time) - timedelta(hours=pad_before)
    end = pd.Timestamp(exit_time) + timedelta(hours=pad_after)
    if end.tz is not None:
        end = end.tz_convert("UTC").tz_localize(None)
        start = start.tz_convert("UTC").tz_localize(None)
    df = yf.download(ticker, start=start - timedelta(days=2),
                     end=end + timedelta(days=2), interval="1h",
                     progress=False, auto_adjust=False)
    df = _normalize(df)
    return df


def draw_chart(trade_row: dict, ann, df_1h: pd.DataFrame, out_path: Path) -> None:
    # Time normalization — everything as tz-naive UTC for plotting
    df = df_1h.copy()
    df.index = df.index.tz_convert("UTC").tz_localize(None) if df.index.tz else df.index
    entry_t = pd.Timestamp(trade_row["entry_time"])
    exit_t = pd.Timestamp(trade_row["exit_time"])
    if entry_t.tz is not None: entry_t = entry_t.tz_convert("UTC").tz_localize(None)
    if exit_t.tz is not None: exit_t = exit_t.tz_convert("UTC").tz_localize(None)

    win = trade_row["pnl_dollar"] > 0
    is_long = trade_row["direction"] == "long"
    entry = float(trade_row["entry_price"])
    sl = float(trade_row["sl"])
    tp1 = float(trade_row["tp1"])
    tp2 = float(trade_row["tp2"])
    tp3 = float(trade_row["tp3"])

    # Figure 1280×720
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=COLOR_BG)
    ax = fig.add_subplot(111)
    ax.set_facecolor(COLOR_BG)

    # ---- Candles ----
    width = 0.025  # candle body width in days
    for ts, row in df.iterrows():
        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        color = COLOR_UP if c >= o else COLOR_DOWN
        # Wick
        ax.plot([ts, ts], [l, h], color=color, linewidth=0.7, zorder=2)
        # Body
        rect = mpatches.Rectangle(
            (mdates.date2num(ts) - width / 2, min(o, c)),
            width, abs(c - o) if c != o else (h - l) * 0.001,
            facecolor=color, edgecolor=color, linewidth=0.5, zorder=3,
        )
        ax.add_patch(rect)

    # ---- OB zone ----
    if ann is not None and ann.ob_low is not None:
        ax.axhspan(ann.ob_low, ann.ob_high, alpha=0.18, color=COLOR_OB, zorder=1)
        ax.text(df.index[1], (ann.ob_low + ann.ob_high) / 2, " Order Block (4H) ",
                color=COLOR_OB, fontsize=8, va="center", fontweight="bold",
                bbox=dict(facecolor=COLOR_BG, edgecolor=COLOR_OB, boxstyle="round,pad=0.2", linewidth=0.5))

    # ---- FVG zone ----
    if ann is not None and ann.fvg_low is not None and ann.fvg_time_start is not None:
        fvg_start = pd.Timestamp(ann.fvg_time_start)
        if fvg_start.tz is not None: fvg_start = fvg_start.tz_convert("UTC").tz_localize(None)
        x0 = mdates.date2num(fvg_start)
        x1 = mdates.date2num(df.index[-1])
        rect = mpatches.Rectangle((x0, ann.fvg_low), x1 - x0, ann.fvg_high - ann.fvg_low,
                                   facecolor=COLOR_FVG, edgecolor=COLOR_FVG,
                                   alpha=0.18, linewidth=0.8, zorder=1.5)
        ax.add_patch(rect)
        ax.text(fvg_start, (ann.fvg_low + ann.fvg_high) / 2, " FVG ",
                color=COLOR_FVG, fontsize=7, va="center", fontweight="bold",
                bbox=dict(facecolor=COLOR_BG, edgecolor=COLOR_FVG, boxstyle="round,pad=0.15", linewidth=0.5))

    # ---- Position box (TradingView long/short tool style) ----
    x0 = mdates.date2num(entry_t)
    x1 = mdates.date2num(exit_t)
    # Profit box: entry → TP3 (target)
    profit_top = max(entry, tp3) if is_long else max(entry, sl)
    profit_bot = min(entry, tp3) if is_long else min(entry, sl)
    if is_long:
        # Green = entry → tp3 (above entry)
        rect_profit = mpatches.Rectangle((x0, entry), x1 - x0, tp3 - entry,
                                          facecolor=COLOR_LONG_BOX, alpha=0.10,
                                          edgecolor=COLOR_LONG_BOX, linewidth=0.6, zorder=1.2)
        # Red = entry → sl (below entry)
        rect_loss = mpatches.Rectangle((x0, sl), x1 - x0, entry - sl,
                                        facecolor=COLOR_LOSS_BOX, alpha=0.10,
                                        edgecolor=COLOR_LOSS_BOX, linewidth=0.6, zorder=1.2)
    else:
        rect_profit = mpatches.Rectangle((x0, tp3), x1 - x0, entry - tp3,
                                          facecolor=COLOR_SHORT_BOX, alpha=0.10,
                                          edgecolor=COLOR_SHORT_BOX, linewidth=0.6, zorder=1.2)
        rect_loss = mpatches.Rectangle((x0, entry), x1 - x0, sl - entry,
                                        facecolor=COLOR_LOSS_BOX, alpha=0.10,
                                        edgecolor=COLOR_LOSS_BOX, linewidth=0.6, zorder=1.2)
    ax.add_patch(rect_profit)
    ax.add_patch(rect_loss)

    # ---- Horizontal level lines ----
    def hline(price, color, label):
        ax.axhline(price, color=color, linewidth=1.1, linestyle=(0, (4, 3)), alpha=0.85, zorder=4)
        ax.text(df.index[-1], price, f"  {label} {price:.1f}",
                color=color, va="center", ha="left", fontsize=8,
                fontweight="bold", zorder=5)

    hline(entry, "#FFFFFF", "Entry")
    hline(sl, COLOR_DOWN, "SL")
    hline(tp1, COLOR_UP, "TP1")
    hline(tp2, "#42B48A", "TP2")
    hline(tp3, "#66BB6A", "TP3")

    # ---- Event markers ----
    def marker(ts_str, label, color, y_offset_frac=0.02):
        if ts_str is None: return
        ts = pd.Timestamp(ts_str)
        if ts.tz is not None: ts = ts.tz_convert("UTC").tz_localize(None)
        if ts < df.index[0] or ts > df.index[-1]: return
        bar = df.iloc[df.index.get_indexer([ts], method="nearest")[0]]
        y = bar["High"] * (1 + y_offset_frac)
        ax.scatter([ts], [y], marker="v", color=color, s=40, zorder=6, edgecolors=COLOR_BG, linewidths=1)
        ax.text(ts, y * (1 + y_offset_frac * 0.5), label, color=color, fontsize=7,
                ha="center", va="bottom", fontweight="bold", zorder=6)

    if ann is not None:
        marker(ann.sweep_time, "SWEEP", "#FFA726", y_offset_frac=0.012)
        marker(ann.leave_time, "OB out", COLOR_TEXT_DIM, y_offset_frac=0.008)
        marker(ann.re_enter_time, "OB in", COLOR_TEXT_DIM, y_offset_frac=0.008)
        marker(ann.bos_time, "BOS", COLOR_OB, y_offset_frac=0.012)

    # ---- Entry/Exit arrows ----
    ax.annotate("ENTRY", xy=(entry_t, entry),
                xytext=(entry_t, entry * (0.992 if is_long else 1.008)),
                color="#FFFFFF", fontsize=8, fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color="#FFFFFF", lw=1.2), zorder=7)
    exit_color = COLOR_UP if win else COLOR_DOWN
    if df.index[0] <= exit_t <= df.index[-1]:
        exit_idx = df.index.get_indexer([exit_t], method="nearest")[0]
        exit_close = float(df.iloc[exit_idx]["Close"])
    else:
        exit_close = entry
    exit_y_text = entry * (1.012 if not is_long else 0.988) if not win else (tp3 if is_long else sl)
    ax.annotate(f"EXIT · {trade_row['exit_reason']}",
                xy=(exit_t, exit_close),
                xytext=(exit_t, exit_y_text),
                color=exit_color, fontsize=8, fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color=exit_color, lw=1.2), zorder=7)

    # ---- Styling ----
    ax.grid(True, color=COLOR_GRID, linewidth=0.5, alpha=0.6)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_color(COLOR_TEXT_FAINT)
    ax.spines["left"].set_visible(False); ax.spines["bottom"].set_color(COLOR_TEXT_FAINT)
    ax.tick_params(colors=COLOR_TEXT_DIM, labelsize=8)
    ax.yaxis.set_label_position("right"); ax.yaxis.tick_right()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))

    # ---- Title bar ----
    n = trade_row.get("n", 0)
    title = (f"#{n}  ·  {trade_row['symbol']}  ·  {trade_row['direction'].upper()}  ·  1H  ·  "
             f"{trade_row['exit_reason']}  ·  R {trade_row['rr_realized']:+.2f}  ·  "
             f"${trade_row['pnl_dollar']:+.0f}")
    fig.text(0.06, 0.945, title, color=COLOR_TEXT, fontsize=12, fontweight="bold")
    subtitle = (f"Entry {entry_t:%Y-%m-%d %H:%M}  →  Exit {exit_t:%Y-%m-%d %H:%M}   ·   "
                f"Confluences: {trade_row['confluences']}")
    fig.text(0.06, 0.918, subtitle, color=COLOR_TEXT_DIM, fontsize=9)

    plt.subplots_adjust(left=0.05, right=0.93, top=0.89, bottom=0.08)
    plt.savefig(out_path, dpi=100, facecolor=COLOR_BG, bbox_inches=None)
    plt.close(fig)


def main():
    root = Path(__file__).parent / "results"
    trades = pd.read_csv(root / "trades_v3_2y.csv",
                         parse_dates=["entry_time", "exit_time"]).sort_values("entry_time").reset_index(drop=True)
    with open(root / "annotations_v3.pkl", "rb") as f:
        annotations: dict = pickle.load(f)

    out = root / "pngs_v3"
    out.mkdir(exist_ok=True)
    print(f"Rendering {len(trades)} 1H screenshots…")

    for i, t in trades.iterrows():
        sym = t["symbol"]
        key = f"{sym}_{pd.Timestamp(t['entry_time']).strftime('%Y%m%d_%H%M')}"
        ann = annotations.get(key)
        try:
            df = fetch_1h_for_trade(sym, t["entry_time"], t["exit_time"])
            if df.empty:
                print(f"  #{i+1}: no data, skipped")
                continue
            row = t.to_dict()
            row["n"] = i + 1
            draw_chart(row, ann, df, out / f"trade-{i+1:03d}.png")
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(trades)}")
        except Exception as e:
            print(f"  #{i+1} ({sym}): {e}")
    print(f"\nAll PNGs: {out}")


if __name__ == "__main__":
    main()
