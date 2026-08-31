from __future__ import annotations

from analysis.indicators import add_indicators
from analysis.nested import nested_grids, split_by_origin
from learning.outcome import label_fib_hold


def compare_origin_holds(df, settings: dict | None = None, key_ratio: float = 0.618) -> dict:
    work = add_indicators(df)
    grids = nested_grids(work, settings)
    grouped = split_by_origin(grids)
    out: dict[str, dict] = {}
    for mode, items in grouped.items():
        labels = [label_fib_hold(work, g, key_ratio=key_ratio) for g in items]
        n = len(labels)
        holds = sum(1 for o in labels if o.success)
        out[mode] = {
            "n": n,
            "holds": holds,
            "hold_rate": (holds / n) if n else None,
        }
    return out
