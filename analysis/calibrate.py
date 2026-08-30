from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from analysis.fibonacci import build_fib_from_leg
from analysis.pivots import Pivot, detect_pivots
from config import ROOT


def load_references(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or (ROOT / "config" / "reference_drawings.yaml")
    with cfg_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def nearest_pivot(
    pivots: list[Pivot],
    price: float,
    kind: str | None = None,
    after: Pivot | None = None,
    before: Pivot | None = None,
) -> Pivot | None:
    candidates = [p for p in pivots if kind is None or p.kind == kind]
    if after is not None:
        candidates = [p for p in candidates if p.index > after.index]
    if before is not None:
        candidates = [p for p in candidates if p.index < before.index]
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p.price - price) / max(price, 1e-9))


def match_drawing(df: pd.DataFrame, drawing: dict[str, Any], method: str, threshold: float) -> dict[str, Any]:
    pivots = detect_pivots(df, method=method, threshold=threshold)
    low_ref = float(drawing["swing_low"])
    high_ref = float(drawing["swing_high"])
    if drawing.get("direction") == "up":
        low_hit = nearest_pivot(pivots, low_ref, "low")
        high_hit = nearest_pivot(pivots, high_ref, "high", after=low_hit)
        if high_hit is None:
            high_hit = nearest_pivot(pivots, high_ref, "high")
            low_hit = nearest_pivot(pivots, low_ref, "low", before=high_hit)
    else:
        high_hit = nearest_pivot(pivots, high_ref, "high")
        low_hit = nearest_pivot(pivots, low_ref, "low", after=high_hit)
        if low_hit is None:
            low_hit = nearest_pivot(pivots, low_ref, "low")
            high_hit = nearest_pivot(pivots, high_ref, "high", before=low_hit)
    low_err = abs(low_hit.price - low_ref) / low_ref if low_hit else 1.0
    high_err = abs(high_hit.price - high_ref) / high_ref if high_hit else 1.0
    grid = None
    ext_err: dict[str, float] = {}
    if low_hit and high_hit:
        start, end = (low_hit, high_hit) if drawing.get("direction") == "up" else (high_hit, low_hit)
        grid = build_fib_from_leg(start, end)
        for name, expected in (drawing.get("expected_extensions") or {}).items():
            ratio = float(name)
            got = grid.extensions.get(ratio)
            if got is None:
                span = end.price - start.price
                got = end.price + span * (ratio - 1.0)
            ext_err[name] = abs(got - float(expected)) / max(float(expected), 1e-9)
    score = 1.0 - min(1.0, 0.5 * low_err + 0.5 * high_err + 0.25 * (sum(ext_err.values()) / max(len(ext_err), 1)))
    return {
        "id": drawing.get("id"),
        "symbol": drawing.get("symbol"),
        "method": method,
        "threshold": threshold,
        "n_pivots": len(pivots),
        "low_ref": low_ref,
        "high_ref": high_ref,
        "low_hit": None if not low_hit else {"price": low_hit.price, "ts": str(low_hit.ts)},
        "high_hit": None if not high_hit else {"price": high_hit.price, "ts": str(high_hit.ts)},
        "low_err_pct": round(low_err * 100, 3),
        "high_err_pct": round(high_err * 100, 3),
        "ext_err_pct": {k: round(v * 100, 3) for k, v in ext_err.items()},
        "score": round(max(0.0, score), 4),
    }


def grid_search(df: pd.DataFrame, drawing: dict[str, Any]) -> dict[str, Any]:
    trials: list[dict[str, Any]] = []
    for method, thresholds in (
        ("pct", (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)),
        ("atr", (1.2, 1.6, 2.0, 2.5, 3.0, 3.5)),
    ):
        for th in thresholds:
            trials.append(match_drawing(df, drawing, method, th))
    trials.sort(key=lambda r: (r["score"], -r["n_pivots"]), reverse=True)
    return {"best": trials[0], "trials": trials}


def calibrate_all(ohlcv_by_symbol: dict[str, pd.DataFrame]) -> dict[str, Any]:
    refs = load_references()
    reports = []
    for drawing in refs.get("drawings", []):
        df = ohlcv_by_symbol.get(drawing["symbol"])
        if df is None or df.empty:
            reports.append({"id": drawing.get("id"), "error": "no_ohlcv"})
            continue
        reports.append(grid_search(df, drawing))
    return {"style": refs.get("style"), "reports": reports}
