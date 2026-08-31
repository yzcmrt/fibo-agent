from __future__ import annotations

from typing import Any

import pandas as pd

from analysis.fibonacci import FibGrid


def dist_to_extreme_now(price: float, grid: FibGrid) -> float:
    rng = max(abs(grid.range), 1e-9)
    return abs(float(price) - float(grid.end.price)) / rng


def tag_is_wick(df: pd.DataFrame, idx: int, level: float, atr: float) -> float:
    row = df.iloc[idx]
    lo, hi, close = float(row["low"]), float(row["high"]), float(row["close"])
    tol = max(atr * 0.25, abs(level) * 0.0005)
    touched = lo - tol <= level <= hi + tol
    body_lo, body_hi = min(close, float(row["open"])), max(close, float(row["open"]))
    body_hit = body_lo - tol <= level <= body_hi + tol
    if touched and not body_hit:
        return 1.0
    return 0.0 if touched else 0.0


def outcome_path_stats(
    df: pd.DataFrame,
    grid: FibGrid,
    *,
    key_ratio: float,
    horizon_bars: int = 24,
    entry_price: float | None = None,
) -> dict[str, float]:
    """Post-touch path. Do not feed into live confluence (lookahead)."""
    empty = {"pct_run": 0.0, "dist_to_extreme": 1.0, "bars_to_ext": 0.0, "tag_wick": 0.0}
    if key_ratio not in grid.levels or grid.end.index + 1 >= len(df):
        return empty
    level = float(grid.levels[key_ratio])
    origin = float(grid.start.price)
    extreme = float(grid.end.price)
    rng = max(abs(extreme - origin), 1e-9)
    atr = float(df["atr14"].iloc[grid.end.index]) if "atr14" in df.columns else rng * 0.02
    if atr != atr or atr <= 0:
        atr = rng * 0.02
    start_i = grid.end.index + 1
    end_i = min(len(df) - 1, grid.end.index + horizon_bars)
    touch_i = None
    for i in range(start_i, end_i + 1):
        lo = float(df["low"].iloc[i])
        hi = float(df["high"].iloc[i])
        if lo - atr * 0.25 <= level <= hi + atr * 0.25:
            touch_i = i
            break
    if touch_i is None:
        return empty
    entry = float(entry_price) if entry_price is not None else level
    best = entry
    best_i = touch_i
    for i in range(touch_i, end_i + 1):
        hi = float(df["high"].iloc[i])
        lo = float(df["low"].iloc[i])
        if grid.direction == "up":
            if hi > best:
                best, best_i = hi, i
        elif lo < best:
            best, best_i = lo, i
    if grid.direction == "up":
        pct_run = (best - entry) / max(abs(entry), 1e-9) * 100.0
    else:
        pct_run = (entry - best) / max(abs(entry), 1e-9) * 100.0
    dist_ext = abs(best - extreme) / rng
    return {
        "pct_run": float(pct_run),
        "dist_to_extreme": float(dist_ext),
        "bars_to_ext": float(best_i - touch_i),
        "tag_wick": tag_is_wick(df, touch_i, level, atr),
    }
