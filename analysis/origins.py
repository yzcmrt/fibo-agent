from __future__ import annotations

from typing import Literal

import pandas as pd

from analysis.pivots import Pivot


OriginMode = Literal["wick", "close"]


def origin_price(df: pd.DataFrame, pivot: Pivot, mode: OriginMode) -> float:
    """User trials both wick tips and body closes when anchoring a fib."""
    if mode == "wick":
        return pivot.price
    row = df.iloc[pivot.index]
    if pivot.kind == "high":
        return float(max(row["open"], row["close"]))
    return float(min(row["open"], row["close"]))


def rebase_pivot(df: pd.DataFrame, pivot: Pivot, mode: OriginMode) -> Pivot:
    return Pivot(
        index=pivot.index,
        ts=pivot.ts,
        price=origin_price(df, pivot, mode),
        kind=pivot.kind,
        method=f"{pivot.method}:{mode}",
        threshold=pivot.threshold,
    )
