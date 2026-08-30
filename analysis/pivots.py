from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Pivot:
    index: int
    ts: pd.Timestamp
    price: float
    kind: Literal["high", "low"]
    method: str
    threshold: float


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def detect_pivots(
    df: pd.DataFrame,
    method: Literal["pct", "atr"] = "pct",
    threshold: float = 0.03,
    atr_period: int = 14,
) -> list[Pivot]:
    """ZigZag-style swing detection. Threshold is percent (0.03 = 3%) or ATR multiple."""
    if df.empty or len(df) < 10:
        return []
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    times = df.index.to_list()
    atr = _atr(df, atr_period).to_numpy() if method == "atr" else None

    pivots: list[Pivot] = []
    last_kind: str | None = None
    last_price = float(df["close"].iloc[0])
    last_idx = 0
    extreme_price = last_price
    extreme_idx = 0

    def crossed(move_from: float, move_to: float, i: int) -> bool:
        if method == "pct":
            if move_from == 0:
                return False
            return abs(move_to - move_from) / abs(move_from) >= threshold
        a = atr[i] if atr is not None and not np.isnan(atr[i]) else np.nan
        if np.isnan(a) or a <= 0:
            return False
        return abs(move_to - move_from) >= threshold * a

    for i in range(1, len(df)):
        if last_kind in (None, "low"):
            if highs[i] > extreme_price:
                extreme_price = highs[i]
                extreme_idx = i
            if crossed(extreme_price, lows[i], i) and lows[i] < extreme_price:
                pivots.append(
                    Pivot(extreme_idx, times[extreme_idx], float(extreme_price), "high", method, threshold)
                )
                last_kind = "high"
                last_price = extreme_price
                last_idx = extreme_idx
                extreme_price = lows[i]
                extreme_idx = i
        if last_kind == "high":
            if lows[i] < extreme_price:
                extreme_price = lows[i]
                extreme_idx = i
            if crossed(extreme_price, highs[i], i) and highs[i] > extreme_price:
                pivots.append(
                    Pivot(extreme_idx, times[extreme_idx], float(extreme_price), "low", method, threshold)
                )
                last_kind = "low"
                last_price = extreme_price
                last_idx = extreme_idx
                extreme_price = highs[i]
                extreme_idx = i

    if extreme_idx != last_idx:
        kind: Literal["high", "low"] = "high" if last_kind in (None, "low") else "low"
        pivots.append(Pivot(extreme_idx, times[extreme_idx], float(extreme_price), kind, method, threshold))
    return pivots
