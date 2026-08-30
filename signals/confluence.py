from __future__ import annotations

from typing import Any

from analysis.fibonacci import FibGrid
from analysis.support_resistance import SRZone
from analysis.trendlines import Trendline
from analysis.volume_profile import VolumeProfile


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_setup(
    price: float,
    grid: FibGrid,
    zones: list[SRZone],
    lines: list[Trendline],
    profile: VolumeProfile | None,
    regime: dict[str, Any],
    model_prob: float | None,
    atr: float,
    weights: dict[str, float],
    bar_index: int,
) -> dict[str, Any]:
    key = {0.382, 0.5, 0.618, 0.786}
    ratio, lvl, dist = grid.nearest_retracement(price)
    tol = max(atr * 0.25, price * 0.001)
    if ratio in key:
        fib_score = _clamp(100.0 * (1.0 - dist / (tol * 4.0)))
        if dist <= tol:
            fib_score = max(fib_score, 80.0)
    else:
        fib_score = _clamp(55.0 * (1.0 - dist / (tol * 6.0)))

    sr_score = 0.0
    for z in zones:
        if z.low - tol <= price <= z.high + tol:
            sr_score = max(sr_score, min(100.0, z.score))
        if z.low - tol <= lvl <= z.high + tol:
            sr_score = max(sr_score, min(100.0, z.score * 0.85 + 10.0))

    tl_score = 0.0
    for ln in lines:
        px = ln.price_at(bar_index)
        if abs(price - px) <= tol * 2:
            tl_score = max(tl_score, ln.score)

    vol_score = 50.0
    if profile:
        if profile.val <= price <= profile.vah:
            vol_score = 62.0
        if abs(price - profile.poc) <= tol * 2:
            vol_score = 80.0

    bias = float(regime.get("alt_bias", 0.0))
    if grid.direction == "up":
        regime_score = 70.0 + 20.0 * bias
    else:
        regime_score = 70.0 - 20.0 * bias
    regime_score = _clamp(regime_score)

    model_score = 50.0 if model_prob is None else _clamp(model_prob * 100.0)

    parts = {
        "fib_proximity": fib_score,
        "sr_overlap": sr_score,
        "trendline": tl_score,
        "volume_oi": vol_score,
        "regime": regime_score,
        "indicator_model": model_score,
    }
    total = 0.0
    wsum = 0.0
    for k, v in parts.items():
        w = float(weights.get(k, 0.0))
        total += w * v
        wsum += w
    score = _clamp(total / max(wsum, 1e-9))
    return {
        "score": score,
        "parts": parts,
        "nearest_ratio": ratio,
        "nearest_price": lvl,
        "distance": dist,
        "direction": grid.direction,
    }
