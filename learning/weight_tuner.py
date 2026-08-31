from __future__ import annotations

from math import sqrt
from typing import Any


FEATURE_TO_WEIGHT = {
    "bb_pct": "bb_position",
    "bb_width": "bb_position",
    "conviction": "bb_position",
    "cvd_slope": "cvd_bias",
    "cvd_div": "cvd_bias",
    "htf_alignment": "htf_alignment",
    "channel_position": "fib_proximity",
    "macro_bias": "regime",
    "origin_is_wick": "fib_proximity",
    "oi_rule": "volume_oi",
    "funding_roc": "volume_oi",
}

CORE_FLOOR = {
    "fib_proximity": 0.12,
    "htf_alignment": 0.06,
}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _var(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def cohens_d(hold: list[float], fail: list[float]) -> float:
    if len(hold) < 3 or len(fail) < 3:
        return 0.0
    pooled = sqrt(
        ((len(hold) - 1) * _var(hold) + (len(fail) - 1) * _var(fail))
        / max(len(hold) + len(fail) - 2, 1)
    )
    if pooled <= 1e-12:
        return 0.0
    return (_mean(hold) - _mean(fail)) / pooled


def feature_delta_table(holds: list[dict[str, float]], fails: list[dict[str, float]], names: list[str]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name in names:
        hvals = [float(r.get(name, 0.0) or 0.0) for r in holds]
        fvals = [float(r.get(name, 0.0) or 0.0) for r in fails]
        if not hvals or not fvals:
            continue
        raw = _mean(hvals) - _mean(fvals)
        d = cohens_d(hvals, fvals)
        out[name] = {
            "hold_mean": round(_mean(hvals), 5),
            "fail_mean": round(_mean(fvals), 5),
            "delta": round(raw, 5),
            "std_delta": round(d, 4),
            "n_hold": float(len(hvals)),
            "n_fail": float(len(fvals)),
        }
    return out


def propose_weights(
    current: dict[str, float],
    deltas: dict[str, dict[str, float]],
    weak: float = 0.15,
    strong: float = 0.40,
) -> dict[str, Any]:
    score: dict[str, list[float]] = {k: [] for k in current}
    for feat, stats in deltas.items():
        target = FEATURE_TO_WEIGHT.get(feat)
        if target not in score:
            continue
        score[target].append(abs(float(stats.get("std_delta") or 0.0)))
    strength = {k: (sum(v) / len(v) if v else 0.0) for k, v in score.items()}

    proposed = dict(current)
    notes = []
    for key, base in current.items():
        s = strength.get(key, 0.0)
        if s < weak:
            proposed[key] = base * 0.40
            notes.append(f"{key} zayıf std_delta={s:.3f} → ağırlık x0.40")
        elif s >= strong:
            proposed[key] = base * 1.35
            notes.append(f"{key} ayırt edici std_delta={s:.3f} → ağırlık x1.35")
        else:
            notes.append(f"{key} nötr std_delta={s:.3f} → aynı")
    for key, floor in CORE_FLOOR.items():
        if key in proposed:
            proposed[key] = max(proposed[key], floor)
    total = sum(proposed.values()) or 1.0
    proposed = {k: round(v / total, 4) for k, v in proposed.items()}
    drift = abs(sum(proposed.values()) - 1.0)
    if drift:
        last = next(reversed(proposed))
        proposed[last] = round(proposed[last] + (1.0 - sum(proposed.values())), 4)
    return {"weights": proposed, "strength": strength, "notes": notes}
