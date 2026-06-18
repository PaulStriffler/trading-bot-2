"""Yahoo Finance data loader for the quick-backtest POC.

Loads 1h, 1d, 1wk bars for the four US indices over the last N weeks.
4H bars are resampled from 1H.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import yfinance as yf

SYMBOL_MAP: dict[str, str] = {
    "US500": "^GSPC",
    "US30": "^DJI",
    "US100": "^NDX",
    "US2000": "^RUT",
}

Interval = Literal["1h", "4h", "1d", "1wk"]


@dataclass
class Bars:
    symbol: str
    h1: pd.DataFrame
    h4: pd.DataFrame
    d1: pd.DataFrame
    w1: pd.DataFrame


def _resample_4h(h1: pd.DataFrame) -> pd.DataFrame:
    """Resample 1H bars to 4H. Anchored at 00:00 UTC."""
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    return h1.resample("4h", label="left", closed="left").agg(agg).dropna()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns multi-index columns when one ticker is passed; flatten."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.dropna()


def fetch(symbol: str, weeks: int = 3) -> Bars:
    """Fetch all timeframes for a symbol over the last `weeks` weeks.

    For 1H we pad with extra history so ATR / swing detection have lookback.
    """
    ticker = SYMBOL_MAP[symbol]
    end = datetime.utcnow()
    # Weekly/Daily need more history for bias detection
    start_long = end - timedelta(weeks=max(weeks * 6, 30))
    # 1H needs some lookback for indicators; yfinance limits 1H to 730 days
    start_1h = end - timedelta(weeks=weeks + 4)

    w1 = _normalize(yf.download(ticker, start=start_long, end=end, interval="1wk", progress=False, auto_adjust=False))
    d1 = _normalize(yf.download(ticker, start=start_long, end=end, interval="1d", progress=False, auto_adjust=False))
    h1 = _normalize(yf.download(ticker, start=start_1h, end=end, interval="1h", progress=False, auto_adjust=False))
    h4 = _resample_4h(h1)

    return Bars(symbol=symbol, h1=h1, h4=h4, d1=d1, w1=w1)


def fetch_long(symbol: str, years: int = 8) -> Bars:
    """Fetch Weekly + Daily for a long-term backtest.

    yfinance 1H is capped at ~730 days, so for 8y we run the strategy in
    "Daily mode": Daily acts as both the confluence- and the entry-timeframe.
    `h4` and `h1` are populated with the daily series so the existing
    strategy/engine code keeps working unchanged.
    """
    ticker = SYMBOL_MAP[symbol]
    end = datetime.utcnow()
    start = end - timedelta(days=years * 365 + 30)
    w1 = _normalize(yf.download(ticker, start=start, end=end, interval="1wk", progress=False, auto_adjust=False))
    d1 = _normalize(yf.download(ticker, start=start, end=end, interval="1d", progress=False, auto_adjust=False))
    return Bars(symbol=symbol, h1=d1.copy(), h4=d1.copy(), d1=d1, w1=w1)


if __name__ == "__main__":
    for sym in SYMBOL_MAP:
        bars = fetch(sym, weeks=3)
        print(f"{sym}: W1={len(bars.w1)} D1={len(bars.d1)} H4={len(bars.h4)} H1={len(bars.h1)}")
