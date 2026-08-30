from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from analysis.pivots import Pivot


@dataclass
class Trendline:
    kind: str  # "support" or "resistance"
    slope: float
    intercept: float
    touches: int
    score: float
    x0: int
    y0: float
    x1: int
    y1: float

    def price_at(self, index: int) -> float:
        return self.slope * index + self.intercept


def detect_trendlines(pivots: list[Pivot], min_touches: int = 2, lookback: int = 12) -> list[Trendline]:
    recent = pivots[-lookback:]
    lows = [p for p in recent if p.kind == "low"]
    highs = [p for p in recent if p.kind == "high"]
    lines: list[Trendline] = []
    if len(lows) >= 2:
        lines.append(_fit("support", lows))
    if len(highs) >= 2:
        lines.append(_fit("resistance", highs))
    return [ln for ln in lines if ln and ln.touches >= min_touches]


def _fit(kind: str, pts: list[Pivot]) -> Trendline:
    xs = np.array([p.index for p in pts], dtype=float)
    ys = np.array([p.price for p in pts], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    pred = slope * xs + intercept
    resid = np.abs(ys - pred)
    scale = np.median(ys) * 0.004 + 1e-9
    inliers = resid <= max(scale, resid.mean() + resid.std())
    touches = int(inliers.sum())
    consistency = float(1.0 / (1.0 + resid.mean() / (np.mean(ys) + 1e-9)))
    score = min(100.0, 40.0 + 15.0 * touches + 30.0 * consistency)
    return Trendline(
        kind=kind,
        slope=float(slope),
        intercept=float(intercept),
        touches=touches,
        score=score,
        x0=int(xs[0]),
        y0=float(ys[0]),
        x1=int(xs[-1]),
        y1=float(ys[-1]),
    )
