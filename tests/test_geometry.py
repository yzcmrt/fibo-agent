from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.fibonacci import build_fib_from_leg
from analysis.pivots import Pivot, detect_pivots
from learning.outcome import label_fib_hold


def _series() -> pd.DataFrame:
    n = 120
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    price = np.linspace(100, 130, 40).tolist() + np.linspace(130, 112, 25).tolist() + np.linspace(112, 140, 55).tolist()
    close = np.array(price, dtype=float)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )
    return df


def test_detect_pivots_finds_swings() -> None:
    df = _series()
    pivots = detect_pivots(df, method="pct", threshold=0.03)
    kinds = [p.kind for p in pivots]
    assert "high" in kinds and "low" in kinds
    assert len(pivots) >= 2


def test_fib_up_leg_618() -> None:
    start = Pivot(0, pd.Timestamp("2024-01-01", tz="UTC"), 100.0, "low", "pct", 0.03)
    end = Pivot(10, pd.Timestamp("2024-01-02", tz="UTC"), 200.0, "high", "pct", 0.03)
    grid = build_fib_from_leg(start, end)
    assert grid.direction == "up"
    assert abs(grid.levels[0.618] - 138.2) < 0.01


def test_label_requires_forward_bars() -> None:
    df = _series()
    start = Pivot(0, df.index[0], float(df["low"].iloc[0]), "low", "pct", 0.03)
    end = Pivot(len(df) - 1, df.index[-1], float(df["high"].iloc[-1]), "high", "pct", 0.03)
    grid = build_fib_from_leg(start, end)
    out = label_fib_hold(df, grid)
    assert out.note == "no_forward_bars"
