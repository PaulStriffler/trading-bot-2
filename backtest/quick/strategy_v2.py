"""Strategy v2 — strict OB-tap + sub-confluence + reaction + BOS.

Differences vs v1:
- Bias: ONLY clean BOS in last 4 weeks OR exact 5-candle streak (no scan-recent memory).
- Entry requires three consecutive conditions after the sweep:
    1. TAP: price returns into the Order Block zone.
    2. SUB-CONFLUENCE: the tap bar wicks into the OB equilibrium (50%-level)
       AND closes back on the "trade side" of that equilibrium.
    3. BOS: the FOLLOWING bar closes beyond the tap bar's extreme in trade direction.
- SL is tighter: below tap-bar low - 0.3 × ATR (long) / above tap-bar high + 0.3 × ATR.
- TPs: TP1 = 1R, TP3 = 4R fixed, TP2 = midpoint.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from .strategy import Setup, Sweep, Trade, atr  # reuse types & helpers


def weekly_bias_strict(df_w: pd.DataFrame, n_streak: int = 5, bos_window: int = 4) -> Literal["bull", "bear", "none"]:
    """Bias = fresh BOS within last `bos_window` weeks OR exact n_streak consecutive closes.

    No long-tail memory: if neither fires in the very recent window, bias = none.
    """
    if len(df_w) < max(n_streak + 1, bos_window + 3):
        return "none"
    # 1. Fresh BOS: latest close beats the high/low of the prior `bos_window` weeks
    recent_close = float(df_w["Close"].iloc[-1])
    prior = df_w.iloc[-(bos_window + 1):-1]
    if recent_close > float(prior["High"].max()):
        return "bull"
    if recent_close < float(prior["Low"].min()):
        return "bear"
    # 2. Exact streak rule
    closes = df_w["Close"].iloc[-(n_streak + 1):].values
    diffs = [closes[i + 1] - closes[i] for i in range(n_streak)]
    if all(d > 0 for d in diffs):
        return "bull"
    if all(d < 0 for d in diffs):
        return "bear"
    return "none"


def find_strict_entry(df: pd.DataFrame, setup: Setup, atr_val: float,
                       tp1_rr: float = 1.0, tp3_r: float = 4.0,
                       sl_atr_buffer: float = 0.3,
                       max_wait_bars: int = 10) -> Trade | None:
    """Walk bars after the sweep looking for OB-tap → sub-confluence → BOS.

    Returns a Trade only if all three conditions fire within max_wait_bars after the sweep.
    """
    after = df[df.index > setup.sweep.time]
    if after.empty or len(after) < 2:
        return None

    ob_low, ob_high = setup.ob_low, setup.ob_high
    ob_eq = (ob_low + ob_high) / 2  # equilibrium / 50%-level of the order block

    for i, (ts, bar) in enumerate(after.iterrows()):
        if i > max_wait_bars:
            return None

        # Condition 1: TAP — bar's range touches OB zone
        tapped = (bar["Low"] <= ob_high) and (bar["High"] >= ob_low)
        if not tapped:
            continue

        # Condition 2: SUB-CONFLUENCE INSIDE OB
        # Long: wick must reach below ob_eq AND close above ob_eq (rejection of the deep half)
        # Short: wick must reach above ob_eq AND close below ob_eq
        if setup.direction == "long":
            sub_conf = (bar["Low"] <= ob_eq) and (bar["Close"] > ob_eq)
        else:
            sub_conf = (bar["High"] >= ob_eq) and (bar["Close"] < ob_eq)
        if not sub_conf:
            continue

        # Condition 3: BOS — next bar closes beyond tap-bar extreme
        if i + 1 >= len(after):
            return None
        next_ts = after.index[i + 1]
        next_bar = after.iloc[i + 1]
        if setup.direction == "long":
            bos = next_bar["Close"] > bar["High"]
        else:
            bos = next_bar["Close"] < bar["Low"]
        if not bos:
            return None  # if BOS doesn't fire on the very next bar, setup invalidated

        # All three conditions met — build the trade
        entry = float(next_bar["Close"])
        if setup.direction == "long":
            sl = float(bar["Low"]) - sl_atr_buffer * atr_val
            risk = entry - sl
            if risk <= 0:
                return None
            tp1 = entry + tp1_rr * risk
            tp3 = entry + tp3_r * risk
        else:
            sl = float(bar["High"]) + sl_atr_buffer * atr_val
            risk = sl - entry
            if risk <= 0:
                return None
            tp1 = entry - tp1_rr * risk
            tp3 = entry - tp3_r * risk
        tp2 = (tp1 + tp3) / 2

        confluences = setup.confluences + ["OB-Tap", "OB-EQ-Reject", "BOS-Confirm"]
        return Trade(setup.symbol, setup.direction, next_ts, entry, sl, tp1, tp2, tp3, confluences)

    return None
