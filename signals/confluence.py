from __future__ import annotations

from typing import Any

from analysis.fibonacci import FibGrid
from analysis.support_resistance import SRZone
from analysis.trendlines import Trendline
from analysis.volume_profile import VolumeProfile


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def normalize_weights(weights: dict[str, float], available: dict[str, bool] | None = None) -> dict[str, float]:
    active = {}
    for key, weight in weights.items():
        if available is not None and available.get(key) is False:
            continue
        if float(weight) <= 0:
            continue
        active[key] = float(weight)
    total = sum(active.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in active.items()}


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
    htf_bias: float = 0.0,
    features: dict[str, Any] | None = None,
    available: dict[str, bool] | None = None,
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

    signed = htf_bias if grid.direction == "up" else -float(htf_bias)
    htf_score = _clamp(50.0 + 50.0 * signed)

    feats = features or {}
    bb_pct = float(feats.get("bb_pct") or 0.5)
    bb_width = float(feats.get("bb_width") or 0.08)
    conviction = float(feats.get("conviction") or 0.0)
    if bb_pct < 0:
        bb_score = 82.0 if grid.direction == "up" else 32.0
    elif bb_pct > 1:
        bb_score = 82.0 if grid.direction == "down" else 32.0
    else:
        bb_score = 50.0 + 20.0 * (0.5 - abs(bb_pct - 0.5))
    if bb_width < 0.04:
        bb_score = _clamp(bb_score + 12.0)
    if conviction >= 1:
        bb_score = _clamp(bb_score + 8.0)

    cvd_slope = float(feats.get("cvd_slope") or 0.0)
    cvd_div = float(feats.get("cvd_div") or 0.0)
    if grid.direction == "up":
        cvd_score = _clamp(50.0 + 25.0 * (1.0 if cvd_slope > 0 else -0.6) - 20.0 * max(cvd_div, 0.0))
    else:
        cvd_score = _clamp(50.0 + 25.0 * (1.0 if cvd_slope < 0 else -0.6) - 20.0 * max(-cvd_div, 0.0))

    parts = {
        "fib_proximity": fib_score,
        "sr_overlap": sr_score,
        "trendline": tl_score,
        "volume_oi": vol_score,
        "regime": regime_score,
        "indicator_model": model_score,
        "htf_alignment": htf_score,
        "bb_position": bb_score,
        "cvd_bias": cvd_score,
    }
    feats = features or {}
    flags = dict(available or {})
    if "cvd_available" in feats and "cvd_bias" not in flags:
        flags["cvd_bias"] = bool(feats.get("cvd_available"))
    used = normalize_weights(weights, flags)
    total = 0.0
    for k, v in parts.items():
        w = float(used.get(k, 0.0))
        total += w * v
    score = _clamp(total if used else 0.0)
    conflict = signed <= -0.25
    if conflict:
        score = min(score, 60.0)
        score = _clamp(score - 18.0)
    return {
        "score": score,
        "parts": parts,
        "nearest_ratio": ratio,
        "nearest_price": lvl,
        "distance": dist,
        "direction": grid.direction,
        "htf_bias": float(htf_bias),
        "htf_conflict": conflict,
        "weights_used": used,
        "disabled": [k for k, ok in flags.items() if ok is False],
    }
