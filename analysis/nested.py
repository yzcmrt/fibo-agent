from __future__ import annotations

from typing import Any

import pandas as pd

from analysis.fibonacci import FibGrid, grids_from_pivots
from analysis.origins import OriginMode, rebase_pivot
from analysis.pivots import detect_pivots


def nested_grids(
    df: pd.DataFrame,
    settings: dict[str, Any] | None = None,
    last_n_legs: int = 6,
) -> list[FibGrid]:
    piv = (settings or {}).get("pivots", {})
    short_pct = float(piv.get("short_pct", 0.03))
    long_pct = float(piv.get("long_pct", 0.08))
    out: list[FibGrid] = []
    for scale, threshold in (("short", short_pct), ("long", long_pct)):
        raw = detect_pivots(df, method="pct", threshold=threshold)
        for mode in ("wick", "close"):
            rebased = [rebase_pivot(df, p, mode) for p in raw]
            for grid in grids_from_pivots(rebased, last_n_legs=last_n_legs):
                grid.origin_mode = mode
                grid.scale = scale
                out.append(grid)
    return out


def split_by_origin(grids: list[FibGrid]) -> dict[OriginMode, list[FibGrid]]:
    grouped: dict[OriginMode, list[FibGrid]] = {"wick": [], "close": []}
    for grid in grids:
        mode = grid.origin_mode if grid.origin_mode in grouped else "wick"
        grouped[mode].append(grid)
    return grouped
