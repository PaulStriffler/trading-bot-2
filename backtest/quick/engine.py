"""Minimal backtest engine for the POC.

- Walks 1H bars after entry; checks TP1/TP2/TP3/SL in order.
- 1% account risk per trade, 33/33/34 partial closes.
- SL moves to break-even after TP1.
- Open trades at end of period are closed at last close (marked "open_close").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .strategy import Trade

PARTIALS = [0.33, 0.33, 0.34]


@dataclass
class TradeResult:
    symbol: str
    direction: str
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    confluences: str
    exit_time: pd.Timestamp
    exit_reason: str         # "tp3", "tp2_sl", "tp1_sl", "sl", "open_close", "margin_rejected"
    rr_realized: float       # weighted R multiple
    pnl_dollar: float        # at 1% risk on $10k → $100 per 1R
    # Sizing & leverage
    position_size: float     # units of the underlying (1 unit = 1 index point per $)
    notional: float          # position_size × entry_price (full exposure in $)
    margin_required: float   # notional / leverage
    leverage_used: float     # notional / balance (effective leverage of this trade)


def simulate(trade: Trade, df_1h: pd.DataFrame, balance: float = 10_000,
             risk_pct: float = 1.0, leverage: float = 30.0) -> TradeResult:
    risk_dollar = balance * risk_pct / 100
    sl_distance = abs(trade.entry_price - trade.sl)
    position_size = risk_dollar / sl_distance if sl_distance > 0 else 0.0
    notional = position_size * trade.entry_price
    margin_required = notional / leverage if leverage > 0 else float("inf")
    leverage_used = notional / balance if balance > 0 else 0.0

    # Broker would reject if margin > available balance
    if margin_required > balance:
        return TradeResult(
            symbol=trade.symbol, direction=trade.direction,
            entry_time=trade.entry_time, entry_price=trade.entry_price,
            sl=trade.sl, tp1=trade.tp1, tp2=trade.tp2, tp3=trade.tp3,
            confluences="+".join(trade.confluences),
            exit_time=trade.entry_time, exit_reason="margin_rejected",
            rr_realized=0.0, pnl_dollar=0.0,
            position_size=position_size, notional=notional,
            margin_required=margin_required, leverage_used=leverage_used,
        )

    after = df_1h[df_1h.index > trade.entry_time]
    sl = trade.sl
    hit_tp1 = hit_tp2 = False
    realized_r = 0.0
    risk_unit = abs(trade.entry_price - trade.sl)

    for ts, bar in after.iterrows():
        h, l = bar["High"], bar["Low"]
        if trade.direction == "long":
            # Order of priority: SL first if both touched in same bar (conservative)
            if l <= sl:
                if hit_tp2:
                    return _result(trade, ts, "tp2_sl", realized_r + PARTIALS[2] * _r(trade.entry_price, sl, "long", risk_unit), risk_dollar, position_size, notional, margin_required, leverage_used)
                if hit_tp1:
                    return _result(trade, ts, "tp1_sl", realized_r + (PARTIALS[1] + PARTIALS[2]) * _r(trade.entry_price, sl, "long", risk_unit), risk_dollar, position_size, notional, margin_required, leverage_used)
                return _result(trade, ts, "sl", -1.0, risk_dollar, position_size, notional, margin_required, leverage_used)
            if not hit_tp1 and h >= trade.tp1:
                realized_r += PARTIALS[0] * 1.0
                sl = trade.entry_price  # move to BE
                hit_tp1 = True
            if hit_tp1 and not hit_tp2 and h >= trade.tp2:
                realized_r += PARTIALS[1] * _r(trade.entry_price, trade.tp2, "long", risk_unit)
                hit_tp2 = True
            if hit_tp2 and h >= trade.tp3:
                realized_r += PARTIALS[2] * _r(trade.entry_price, trade.tp3, "long", risk_unit)
                return _result(trade, ts, "tp3", realized_r, risk_dollar, position_size, notional, margin_required, leverage_used)
        else:  # short
            if h >= sl:
                if hit_tp2:
                    return _result(trade, ts, "tp2_sl", realized_r + PARTIALS[2] * _r(trade.entry_price, sl, "short", risk_unit), risk_dollar, position_size, notional, margin_required, leverage_used)
                if hit_tp1:
                    return _result(trade, ts, "tp1_sl", realized_r + (PARTIALS[1] + PARTIALS[2]) * _r(trade.entry_price, sl, "short", risk_unit), risk_dollar, position_size, notional, margin_required, leverage_used)
                return _result(trade, ts, "sl", -1.0, risk_dollar, position_size, notional, margin_required, leverage_used)
            if not hit_tp1 and l <= trade.tp1:
                realized_r += PARTIALS[0] * 1.0
                sl = trade.entry_price
                hit_tp1 = True
            if hit_tp1 and not hit_tp2 and l <= trade.tp2:
                realized_r += PARTIALS[1] * _r(trade.entry_price, trade.tp2, "short", risk_unit)
                hit_tp2 = True
            if hit_tp2 and l <= trade.tp3:
                realized_r += PARTIALS[2] * _r(trade.entry_price, trade.tp3, "short", risk_unit)
                return _result(trade, ts, "tp3", realized_r, risk_dollar, position_size, notional, margin_required, leverage_used)

    # End of data — close remainder at last close
    last_ts = after.index[-1] if not after.empty else trade.entry_time
    last_close = after["Close"].iloc[-1] if not after.empty else trade.entry_price
    remaining = 1.0 - sum(PARTIALS[: (2 if hit_tp2 else 1 if hit_tp1 else 0)])
    realized_r += remaining * _r(trade.entry_price, last_close, trade.direction, risk_unit)
    return _result(trade, last_ts, "open_close", realized_r, risk_dollar, position_size, notional, margin_required, leverage_used)


def _r(entry: float, price: float, direction: str, risk_unit: float) -> float:
    if direction == "long":
        return (price - entry) / risk_unit
    return (entry - price) / risk_unit


def _result(trade: Trade, exit_time, reason: str, realized_r: float, risk_dollar: float,
            position_size: float, notional: float, margin_required: float, leverage_used: float) -> TradeResult:
    return TradeResult(
        symbol=trade.symbol,
        direction=trade.direction,
        entry_time=trade.entry_time,
        entry_price=trade.entry_price,
        sl=trade.sl,
        tp1=trade.tp1,
        tp2=trade.tp2,
        tp3=trade.tp3,
        confluences="+".join(trade.confluences),
        exit_time=exit_time,
        exit_reason=reason,
        rr_realized=realized_r,
        pnl_dollar=realized_r * risk_dollar,
        position_size=position_size,
        notional=notional,
        margin_required=margin_required,
        leverage_used=leverage_used,
    )
