from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from analysis.fibonacci import grids_from_pivots
from analysis.indicators import add_indicators, snapshot_features
from analysis.origins import rebase_pivot
from analysis.pivots import detect_pivots
from learning.outcome import label_fib_hold


HOLD_FEATURES = [
    "rsi14",
    "ema_trend",
    "vol_z",
    "atr_pct",
    "ret_12",
    "ema20_slope",
    "close_vs_ema50",
    "fib_ratio",
]


def _extra_features(df: pd.DataFrame, idx: int) -> dict[str, float]:
    row = df.iloc[idx]
    close = float(row["close"])
    ema50 = float(row["ema55"]) if row.get("ema55") == row.get("ema55") else close
    ema21 = float(row["ema21"]) if row.get("ema21") == row.get("ema21") else close
    prev_ema = float(df["ema21"].iloc[max(0, idx - 3)]) if idx >= 3 else ema21
    return {
        "ema20_slope": (ema21 - prev_ema) / max(abs(prev_ema), 1e-9),
        "close_vs_ema50": (close - ema50) / max(abs(ema50), 1e-9),
        "atr_pct": float(row.get("atr14") or 0.0) / max(close, 1e-9),
    }


def mine_hold_correlations(
    df: pd.DataFrame,
    params: dict[str, Any] | None = None,
    origin_mode: str = "wick",
    key_ratios: tuple[float, ...] = (0.382, 0.5, 0.618, 0.786, 1.618),
) -> dict[str, Any]:
    """When a fib level is tagged, snapshot indicators and split hold vs fail."""
    params = params or {"method": "pct", "threshold": 0.05, "horizon_bars": 24, "touch_tolerance_atr": 0.3, "min_continuation_r": 1.0}
    work = add_indicators(df)
    raw_pivots = detect_pivots(work, method=params["method"], threshold=float(params["threshold"]))
    pivots = [rebase_pivot(work, p, "close" if origin_mode == "close" else "wick") for p in raw_pivots]
    grids = grids_from_pivots(pivots, last_n_legs=max(8, len(pivots)))

    holds: list[dict[str, float]] = []
    fails: list[dict[str, float]] = []
    by_ratio: dict[str, dict[str, int]] = defaultdict(lambda: {"hold": 0, "fail": 0, "touch": 0})

    for grid in grids:
        if grid.end.index < 80:
            continue
        if grid.range / max(grid.end.price, 1e-9) < 0.03:
            continue
        for ratio in key_ratios:
            if ratio > 1:
                # treat extension as a target touch from the end bar forward using a synthetic retracement label
                level = grid.extensions.get(ratio)
                if level is None:
                    continue
                # reuse hold logic by temporarily putting the extension into levels
                grid.levels[ratio] = level
            if ratio not in grid.levels:
                continue
            out = label_fib_hold(
                work,
                grid,
                key_ratio=ratio if ratio <= 1 else 0.618,
                horizon_bars=int(params.get("horizon_bars", 24)),
                touch_tolerance_atr=float(params.get("touch_tolerance_atr", 0.3)),
                min_continuation_r=float(params.get("min_continuation_r", 1.0)),
            )
            # For extensions, success = price reached the extension before invalidation of origin
            if ratio > 1:
                start_i = grid.end.index + 1
                end_i = min(len(work) - 1, grid.end.index + int(params.get("horizon_bars", 24)))
                touched = False
                success = False
                for i in range(start_i, end_i + 1):
                    lo = float(work["low"].iloc[i])
                    hi = float(work["high"].iloc[i])
                    if lo <= level <= hi:
                        touched = True
                    if grid.direction == "up" and hi >= level:
                        touched = True
                        success = True
                        break
                    if grid.direction == "down" and lo <= level:
                        touched = True
                        success = True
                        break
                    if grid.direction == "up" and lo < grid.start.price:
                        break
                    if grid.direction == "down" and hi > grid.start.price:
                        break
                out_success, out_touched = success, touched
                idx = min(grid.end.index, len(work) - 1)
            else:
                out_success, out_touched = out.success, out.touched
                idx = grid.end.index
            if not out_touched:
                continue
            key = f"{ratio:.3f}"
            by_ratio[key]["touch"] += 1
            feats = snapshot_features(work, idx)
            feats.update(_extra_features(work, idx))
            feats["fib_ratio"] = float(ratio)
            if out_success:
                by_ratio[key]["hold"] += 1
                holds.append(feats)
            else:
                by_ratio[key]["fail"] += 1
                fails.append(feats)

    comparison: dict[str, dict[str, float]] = {}
    for name in HOLD_FEATURES:
        hvals = [r.get(name, 0.0) or 0.0 for r in holds]
        fvals = [r.get(name, 0.0) or 0.0 for r in fails]
        if not hvals or not fvals:
            continue
        hmean = sum(hvals) / len(hvals)
        fmean = sum(fvals) / len(fvals)
        comparison[name] = {
            "hold_mean": round(hmean, 5),
            "fail_mean": round(fmean, 5),
            "delta": round(hmean - fmean, 5),
        }

    rules = []
    for name, stats in sorted(comparison.items(), key=lambda kv: abs(kv[1]["delta"]), reverse=True):
        if abs(stats["delta"]) < 1e-6:
            continue
        side = "daha yüksek" if stats["delta"] > 0 else "daha düşük"
        rules.append(
            f"Fib hold olduğunda {name} fail'e göre {side} "
            f"(hold {stats['hold_mean']}, fail {stats['fail_mean']})."
        )

    return {
        "origin_mode": origin_mode,
        "n_hold": len(holds),
        "n_fail": len(fails),
        "by_ratio": dict(by_ratio),
        "feature_delta": comparison,
        "rules": rules[:8],
    }
