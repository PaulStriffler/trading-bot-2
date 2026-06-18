"""Minimal POC implementation of the ICT/SMC strategy.

Simplifications (documented for transparency):
- News filter: skipped.
- Bias: uses the "5 consecutive weekly closes" alternative rule (simplest, fewest false signals).
- Confluences: Order Block + FVG + BOS implemented. BPR/Equilibrium skipped → min_required = 2 means OB + (FVG or BOS).
- Entry: when price taps the OB zone after sweep and 1H makes BOS in trade direction.
- SL: sweep extreme ± 0.5 × ATR(4H).
- TPs: TP1 = 1R, TP3 = next opposing daily liquidity (recent swing), TP2 = midpoint.

These match the spirit of the masterplan; the production version in Phase 3 will be more rigorous.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

Direction = Literal["long", "short"]


@dataclass
class Sweep:
    direction: Direction          # "long" sweep = a low was swept (we trade long)
    time: pd.Timestamp            # candle that did the sweep
    sweep_level: float            # the low/high that was taken out
    extreme: float                # the actual extreme reached by the sweeping candle


@dataclass
class Setup:
    symbol: str
    direction: Direction
    sweep: Sweep
    ob_high: float
    ob_low: float
    confluences: list[str] = field(default_factory=list)


@dataclass
class Trade:
    symbol: str
    direction: Direction
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    confluences: list[str]


# ---------- helpers ----------

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h_l = df["High"] - df["Low"]
    h_pc = (df["High"] - df["Close"].shift()).abs()
    l_pc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


# ---------- step 1: weekly bias ----------

def weekly_bias(df_w: pd.DataFrame, n: int = 5, swing_lookback: int = 6, scan_recent: int = 8) -> Literal["bull", "bear", "none"]:
    """Bias = BOS rule OR 5 consecutive closes rule (masterplan §1).

    Bias is set by the MOST RECENT BOS within the last `scan_recent` weeks
    and remains in force until the opposite BOS occurs. This mirrors how
    a manual trader carries a bias forward through pullbacks.
    """
    if len(df_w) < max(n + 1, swing_lookback + 2):
        return "none"

    last_bias: str = "none"
    # Walk forward through the recent window and update bias on each BOS event.
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

    # Fallback: 5 consecutive closes rule
    closes = df_w["Close"].iloc[-(n + 1):].values
    diffs = [closes[i + 1] - closes[i] for i in range(n)]
    if all(d > 0 for d in diffs):
        return "bull"
    if all(d < 0 for d in diffs):
        return "bear"
    return "none"


# ---------- step 2: daily sweeps ----------

def find_daily_sweeps(df_d: pd.DataFrame, bias: str, window: int = 21) -> list[Sweep]:
    """Find daily liquidity sweeps inside the last `window` days.

    Long setup: down-candle then up-candle form a daily low; a later candle's
    low pierces that low (sweep) and closes above it.
    Short: mirror.
    """
    sweeps: list[Sweep] = []
    df = df_d.iloc[-window:]
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]

    if bias == "bull":
        # iterate looking for pivot lows (i-2 down, i-1 up) then sweep later
        for i in range(2, len(df) - 1):
            is_pivot = (c.iloc[i - 2] < o.iloc[i - 2]) and (c.iloc[i - 1] > o.iloc[i - 1])
            if not is_pivot:
                continue
            pivot_low = min(l.iloc[i - 2], l.iloc[i - 1])
            # look ahead for sweep within next 7 candles
            for j in range(i, min(i + 7, len(df))):
                if l.iloc[j] < pivot_low and c.iloc[j] > pivot_low:
                    sweeps.append(Sweep("long", df.index[j], pivot_low, l.iloc[j]))
                    break
    elif bias == "bear":
        for i in range(2, len(df) - 1):
            is_pivot = (c.iloc[i - 2] > o.iloc[i - 2]) and (c.iloc[i - 1] < o.iloc[i - 1])
            if not is_pivot:
                continue
            pivot_high = max(h.iloc[i - 2], h.iloc[i - 1])
            for j in range(i, min(i + 7, len(df))):
                if h.iloc[j] > pivot_high and c.iloc[j] < pivot_high:
                    sweeps.append(Sweep("short", df.index[j], pivot_high, h.iloc[j]))
                    break
    return sweeps


# ---------- step 3: 4H confluences ----------

def find_order_block(df_4h: pd.DataFrame, sweep: Sweep) -> tuple[float, float] | None:
    """OB = the last opposite-color 4H candle before the sweeping move.

    Long: last down-close 4H candle just before sweep time → OB zone [low, high].
    Short: last up-close 4H candle.
    """
    before = df_4h[df_4h.index <= sweep.time]
    if before.empty:
        return None
    if sweep.direction == "long":
        downs = before[before["Close"] < before["Open"]]
        if downs.empty:
            return None
        ob = downs.iloc[-1]
    else:
        ups = before[before["Close"] > before["Open"]]
        if ups.empty:
            return None
        ob = ups.iloc[-1]
    return float(ob["Low"]), float(ob["High"])


def has_fvg(df_4h: pd.DataFrame, sweep: Sweep) -> bool:
    """3-candle FVG anywhere in the 6 candles leading up to / around the sweep.

    Bullish FVG: candle[i+1].low > candle[i-1].high.
    Bearish FVG: candle[i+1].high < candle[i-1].low.
    """
    idx = df_4h.index.get_indexer([sweep.time], method="nearest")[0]
    lo = max(idx - 6, 1)
    hi = min(idx + 1, len(df_4h) - 1)
    for i in range(lo, hi):
        if i + 1 >= len(df_4h) or i - 1 < 0:
            continue
        prev_high = df_4h["High"].iloc[i - 1]
        prev_low = df_4h["Low"].iloc[i - 1]
        next_high = df_4h["High"].iloc[i + 1]
        next_low = df_4h["Low"].iloc[i + 1]
        if sweep.direction == "long" and next_low > prev_high:
            return True
        if sweep.direction == "short" and next_high < prev_low:
            return True
    return False


def has_4h_bos(df_4h: pd.DataFrame, sweep: Sweep) -> bool:
    """After the sweep, does 4H close beyond the recent swing in trade direction?"""
    after = df_4h[df_4h.index > sweep.time]
    if len(after) < 2:
        return False
    before = df_4h[df_4h.index <= sweep.time].tail(10)
    if before.empty:
        return False
    if sweep.direction == "long":
        recent_high = float(before["High"].max())
        return bool((after["Close"] > recent_high).any())
    else:
        recent_low = float(before["Low"].min())
        return bool((after["Close"] < recent_low).any())


def build_setup(df_4h: pd.DataFrame, sweep: Sweep, symbol: str, min_confluences: int = 2) -> Setup | None:
    ob = find_order_block(df_4h, sweep)
    if ob is None:
        return None
    confluences = ["OB"]
    if has_fvg(df_4h, sweep):
        confluences.append("FVG")
    if has_4h_bos(df_4h, sweep):
        confluences.append("BOS")
    if len(confluences) < min_confluences:
        return None
    return Setup(symbol=symbol, direction=sweep.direction, sweep=sweep,
                 ob_low=ob[0], ob_high=ob[1], confluences=confluences)


# ---------- step 4: 1H entry ----------

def find_entry(df_1h: pd.DataFrame, setup: Setup, atr_4h: float) -> Trade | None:
    """Wait for price to tap OB, then enter on the next 1H bar."""
    after = df_1h[df_1h.index > setup.sweep.time]
    if after.empty:
        return None
    for ts, bar in after.iterrows():
        in_zone = bar["Low"] <= setup.ob_high and bar["High"] >= setup.ob_low
        if not in_zone:
            continue
        # Entry at OB edge (conservative)
        if setup.direction == "long":
            entry = setup.ob_high
            sl = setup.sweep.extreme - 0.5 * atr_4h
            risk = entry - sl
            if risk <= 0:
                return None
            tp1 = entry + risk
            tp3 = float(df_1h["High"].iloc[max(0, df_1h.index.get_loc(ts) - 30):df_1h.index.get_loc(ts)].max())
            if tp3 <= tp1:
                tp3 = entry + 3 * risk
            tp2 = (tp1 + tp3) / 2
        else:
            entry = setup.ob_low
            sl = setup.sweep.extreme + 0.5 * atr_4h
            risk = sl - entry
            if risk <= 0:
                return None
            tp1 = entry - risk
            tp3 = float(df_1h["Low"].iloc[max(0, df_1h.index.get_loc(ts) - 30):df_1h.index.get_loc(ts)].min())
            if tp3 >= tp1:
                tp3 = entry - 3 * risk
            tp2 = (tp1 + tp3) / 2

        return Trade(setup.symbol, setup.direction, ts, entry, sl, tp1, tp2, tp3, setup.confluences)
    return None
