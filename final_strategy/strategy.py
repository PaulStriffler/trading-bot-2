"""Strategy v3 — FINAL (full multi-timeframe).

Implements the documented strategy from docs/Tradingstrategie_neu_final.md:

  Weekly bias → Daily liquidity sweep → 4H Order Block →
  1H sequence: LEAVE_OB → RE-ENTER_OB → FVG_INSIDE → BOS_OUT → ENTRY

SL: OB-extreme ± 0.5 × ATR(4H)
TP1: 1R
TP3: next opposing daily-swing PAL (or fixed 4R fallback)
TP2: midpoint
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import pandas as pd

from .strategy_base import Setup, Sweep, Trade, atr  # reuse types


# ---------- Annotation payload (drawn on the 1H screenshot) ----------
@dataclass
class V3Annotations:
    symbol: str
    direction: str
    sweep_time: pd.Timestamp
    sweep_level: float
    ob_low: float
    ob_high: float
    ob_time_start: Optional[pd.Timestamp] = None
    ob_time_end: Optional[pd.Timestamp] = None
    leave_time: Optional[pd.Timestamp] = None
    re_enter_time: Optional[pd.Timestamp] = None
    fvg_low: Optional[float] = None
    fvg_high: Optional[float] = None
    fvg_time_start: Optional[pd.Timestamp] = None
    fvg_time_end: Optional[pd.Timestamp] = None
    bos_level: Optional[float] = None
    bos_time: Optional[pd.Timestamp] = None
    fib_a: Optional[float] = None   # swing low (long) / high (short)
    fib_b: Optional[float] = None   # swing high (long) / low (short)
    fib_c: Optional[float] = None   # local extreme before entry


# ---------- Weekly bias (carries through pullbacks like a manual trader) ----------
def weekly_bias_v3(df_w: pd.DataFrame, n: int = 5, swing_lookback: int = 6, scan_recent: int = 12) -> Literal["bull", "bear", "none"]:
    """Persistent bias: last BOS within scan_recent weeks OR n consecutive closes."""
    if len(df_w) < max(n + 1, swing_lookback + 2):
        return "none"
    last_bias: str = "none"
    start = max(swing_lookback, len(df_w) - scan_recent)
    for i in range(start, len(df_w)):
        prior = df_w.iloc[i - swing_lookback:i]
        if prior.empty:
            continue
        c = float(df_w["Close"].iloc[i])
        if c > float(prior["High"].max()):
            last_bias = "bull"
        elif c < float(prior["Low"].min()):
            last_bias = "bear"
    if last_bias != "none":
        return last_bias  # type: ignore[return-value]
    closes = df_w["Close"].iloc[-(n + 1):].values
    diffs = [closes[i + 1] - closes[i] for i in range(n)]
    if all(d > 0 for d in diffs):
        return "bull"
    if all(d < 0 for d in diffs):
        return "bear"
    return "none"


# ---------- OB on 4H ----------
def find_ob_4h(df_4h: pd.DataFrame, sweep: Sweep) -> Optional[tuple[float, float, pd.Timestamp]]:
    """Last opposite-color 4H candle BEFORE the sweep.

    Returns (ob_low, ob_high, ob_time) or None.
    """
    before = df_4h[df_4h.index <= sweep.time]
    if before.empty:
        return None
    if sweep.direction == "long":
        downs = before[before["Close"] < before["Open"]]
        if downs.empty:
            return None
        ob = downs.iloc[-1]
        return float(ob["Low"]), float(ob["High"]), ob.name
    ups = before[before["Close"] > before["Open"]]
    if ups.empty:
        return None
    ob = ups.iloc[-1]
    return float(ob["Low"]), float(ob["High"]), ob.name


# ---------- Find next PAL (opposing daily swing) ----------
def next_daily_pal(df_d: pd.DataFrame, sweep: Sweep, lookback: int = 30) -> Optional[float]:
    """Next previous-area-of-liquidity in trade direction.

    For long: the highest high of the last `lookback` days BEFORE the sweep.
    For short: the lowest low.
    """
    before = df_d[df_d.index < sweep.time].tail(lookback)
    if before.empty:
        return None
    if sweep.direction == "long":
        return float(before["High"].max())
    return float(before["Low"].min())


# ---------- The core 1H sequence ----------
def find_entry_v3(df_1h: pd.DataFrame, df_d: pd.DataFrame, sweep: Sweep, symbol: str,
                  ob_low: float, ob_high: float, ob_time: pd.Timestamp,
                  atr_4h: float, sl_atr_buffer: float = 0.5,
                  max_wait_bars: int = 80) -> Optional[tuple[Trade, V3Annotations]]:
    """Run the LEAVE → RE-ENTER → FVG → BOS sequence on 1H after the sweep."""
    after = df_1h[df_1h.index > sweep.time]
    if len(after) < 5:
        return None
    direction = sweep.direction

    state = "wait_leave"
    leave_time: Optional[pd.Timestamp] = None
    re_enter_time: Optional[pd.Timestamp] = None
    re_enter_idx: int = -1
    fvg_low: Optional[float] = None
    fvg_high: Optional[float] = None
    fvg_time_start: Optional[pd.Timestamp] = None
    fvg_time_end: Optional[pd.Timestamp] = None

    bars = after.iloc[:max_wait_bars]
    for i in range(len(bars)):
        ts = bars.index[i]
        bar = bars.iloc[i]

        if state == "wait_leave":
            # Long: price must move ABOVE OB high; Short: BELOW OB low
            if direction == "long" and bar["High"] > ob_high:
                leave_time = ts
                state = "wait_re_enter"
            elif direction == "short" and bar["Low"] < ob_low:
                leave_time = ts
                state = "wait_re_enter"

        elif state == "wait_re_enter":
            # Need to come back INTO the OB zone
            if direction == "long" and bar["Low"] <= ob_high:
                re_enter_time = ts
                re_enter_idx = i
                state = "scan_fvg"
            elif direction == "short" and bar["High"] >= ob_low:
                re_enter_time = ts
                re_enter_idx = i
                state = "scan_fvg"

        elif state == "scan_fvg":
            # FVG inside (or overlapping) the OB, formed during the return move.
            # 3-candle pattern: candle[i-2] and candle[i] leave a gap, candle[i-1] is impulse.
            if i < re_enter_idx + 2:
                continue
            c0 = bars.iloc[i - 2]
            c2 = bars.iloc[i]
            if direction == "long":
                # bullish FVG: c2.low > c0.high (gap up)
                if c2["Low"] > c0["High"]:
                    # at least part of FVG must overlap OB zone (within ob_low..ob_high or adjacent)
                    if c2["Low"] <= ob_high + 0.5 * (ob_high - ob_low):  # tolerance
                        fvg_low = float(c0["High"])
                        fvg_high = float(c2["Low"])
                        fvg_time_start = bars.index[i - 2]
                        fvg_time_end = bars.index[i]
                        state = "wait_bos"
            else:
                if c2["High"] < c0["Low"]:
                    if c2["High"] >= ob_low - 0.5 * (ob_high - ob_low):
                        fvg_low = float(c2["High"])
                        fvg_high = float(c0["Low"])
                        fvg_time_start = bars.index[i - 2]
                        fvg_time_end = bars.index[i]
                        state = "wait_bos"

        elif state == "wait_bos":
            # Close beyond the recent micro-swing in trade direction
            window = bars.iloc[max(0, i - 8):i]
            if window.empty:
                continue
            if direction == "long":
                bos_level = float(window["High"].max())
                if bar["Close"] > bos_level:
                    entry = float(bar["Close"])
                    sl = ob_low - sl_atr_buffer * atr_4h
                    risk = entry - sl
                    if risk <= 0:
                        return None
                    tp1 = entry + risk
                    pal = next_daily_pal(df_d, sweep)
                    fib_c = float(window["Low"].min())
                    if pal and pal > tp1:
                        tp3 = pal
                    else:
                        # Fib extension fallback (long)
                        swing_lo = float(df_d.iloc[-60:]["Low"].min())
                        swing_hi = float(df_d.iloc[-60:]["High"].max())
                        if swing_hi > swing_lo:
                            tp3 = entry + 1.618 * (swing_hi - swing_lo) * 0.1
                            if tp3 <= tp1:
                                tp3 = entry + 4 * risk
                        else:
                            tp3 = entry + 4 * risk
                    tp2 = (tp1 + tp3) / 2
                    confluences = ["OB", "OB-Leave", "OB-Reenter", "FVG-Inside", "BOS"]
                    ann = V3Annotations(
                        symbol=symbol, direction=direction,
                        sweep_time=sweep.time, sweep_level=sweep.sweep_level,
                        ob_low=ob_low, ob_high=ob_high,
                        ob_time_start=ob_time, ob_time_end=ob_time,
                        leave_time=leave_time, re_enter_time=re_enter_time,
                        fvg_low=fvg_low, fvg_high=fvg_high,
                        fvg_time_start=fvg_time_start, fvg_time_end=fvg_time_end,
                        bos_level=bos_level, bos_time=ts,
                    )
                    return Trade(symbol, direction, ts, entry, sl, tp1, tp2, tp3, confluences), ann
            else:
                bos_level = float(window["Low"].min())
                if bar["Close"] < bos_level:
                    entry = float(bar["Close"])
                    sl = ob_high + sl_atr_buffer * atr_4h
                    risk = sl - entry
                    if risk <= 0:
                        return None
                    tp1 = entry - risk
                    pal = next_daily_pal(df_d, sweep)
                    if pal and pal < tp1:
                        tp3 = pal
                    else:
                        swing_lo = float(df_d.iloc[-60:]["Low"].min())
                        swing_hi = float(df_d.iloc[-60:]["High"].max())
                        if swing_hi > swing_lo:
                            tp3 = entry - 1.618 * (swing_hi - swing_lo) * 0.1
                            if tp3 >= tp1:
                                tp3 = entry - 4 * risk
                        else:
                            tp3 = entry - 4 * risk
                    tp2 = (tp1 + tp3) / 2
                    confluences = ["OB", "OB-Leave", "OB-Reenter", "FVG-Inside", "BOS"]
                    ann = V3Annotations(
                        symbol=symbol, direction=direction,
                        sweep_time=sweep.time, sweep_level=sweep.sweep_level,
                        ob_low=ob_low, ob_high=ob_high,
                        ob_time_start=ob_time, ob_time_end=ob_time,
                        leave_time=leave_time, re_enter_time=re_enter_time,
                        fvg_low=fvg_low, fvg_high=fvg_high,
                        fvg_time_start=fvg_time_start, fvg_time_end=fvg_time_end,
                        bos_level=bos_level, bos_time=ts,
                    )
                    return Trade(symbol, direction, ts, entry, sl, tp1, tp2, tp3, confluences), ann

    return None
