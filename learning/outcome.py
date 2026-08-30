from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analysis.fibonacci import FibGrid


@dataclass
class Outcome:
    touched: bool
    success: bool
    r_multiple: float
    mfe: float
    mae: float
    bars_to_resolution: int
    entry_price: float | None
    note: str


def label_fib_hold(
    df: pd.DataFrame,
    grid: FibGrid,
    key_ratio: float = 0.618,
    horizon_bars: int = 24,
    touch_tolerance_atr: float = 0.25,
    min_continuation_r: float = 1.0,
) -> Outcome:
    """
    A drawn fib is 'successful' when price later tags the key retracement
    and then continues in the original swing direction by at least min_continuation_r
    *before* invalidating beyond the swing origin.
    """
    if grid.end.index + 2 >= len(df):
        return Outcome(False, False, 0.0, 0.0, 0.0, 0, None, "no_forward_bars")

    level = grid.levels[key_ratio]
    origin = grid.start.price
    extreme = grid.end.price
    start_i = grid.end.index + 1
    end_i = min(len(df) - 1, grid.end.index + horizon_bars)
    atr = float(df["atr14"].iloc[grid.end.index]) if "atr14" in df.columns else abs(extreme - origin) * 0.02
    if atr != atr or atr <= 0:
        atr = abs(extreme - origin) * 0.02
    tol = atr * touch_tolerance_atr

    touched = False
    entry = None
    entry_i = None
    for i in range(start_i, end_i + 1):
        lo = float(df["low"].iloc[i])
        hi = float(df["high"].iloc[i])
        if lo - tol <= level <= hi + tol:
            touched = True
            entry = level
            entry_i = i
            break
        # already invalidated before first touch
        if grid.direction == "up" and lo < origin - tol:
            return Outcome(False, False, 0.0, 0.0, abs(lo - extreme) / max(atr, 1e-9), i - start_i, None, "broke_origin_before_touch")
        if grid.direction == "down" and hi > origin + tol:
            return Outcome(False, False, 0.0, 0.0, abs(hi - extreme) / max(atr, 1e-9), i - start_i, None, "broke_origin_before_touch")

    if not touched or entry is None or entry_i is None:
        return Outcome(False, False, 0.0, 0.0, 0.0, end_i - start_i, None, "no_touch")

    risk = abs(entry - origin)
    if risk <= 0:
        return Outcome(True, False, 0.0, 0.0, 0.0, 0, entry, "zero_risk")
    target = entry + (extreme - entry)  # back to swing end first; R measured vs origin
    # 1R target = risk distance in trend direction from entry
    if grid.direction == "up":
        r1 = entry + risk * min_continuation_r
    else:
        r1 = entry - risk * min_continuation_r

    mfe = 0.0
    mae = 0.0
    for i in range(entry_i + 1, end_i + 1):
        lo = float(df["low"].iloc[i])
        hi = float(df["high"].iloc[i])
        if grid.direction == "up":
            mfe = max(mfe, (hi - entry) / risk)
            mae = max(mae, (entry - lo) / risk)
            if lo <= origin - tol:
                return Outcome(True, False, -1.0, mfe, mae, i - entry_i, entry, "invalidated")
            if hi >= r1:
                return Outcome(True, True, float(mfe), mfe, mae, i - entry_i, entry, "target_hit")
        else:
            mfe = max(mfe, (entry - lo) / risk)
            mae = max(mae, (hi - entry) / risk)
            if hi >= origin + tol:
                return Outcome(True, False, -1.0, mfe, mae, i - entry_i, entry, "invalidated")
            if lo <= r1:
                return Outcome(True, True, float(mfe), mfe, mae, i - entry_i, entry, "target_hit")

    success = mfe >= min_continuation_r
    return Outcome(True, success, float(mfe if success else mfe), mfe, mae, end_i - entry_i, entry, "timeout_mfe")
