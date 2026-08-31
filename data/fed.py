from __future__ import annotations

import re
from typing import Any


def _mid(bucket: str) -> float | None:
    nums = re.findall(r"(\d+(?:\.\d+)?)", bucket)
    if len(nums) < 2:
        return None
    return (float(nums[0]) + float(nums[1])) / 2.0


def summarize_meetings(payload: dict[str, Any]) -> tuple[float | None, float | None, str]:
    meetings = payload.get("meetings") or []
    if not meetings:
        return None, None, "fed:empty"
    first = meetings[0]
    probs = first.get("probabilities") or {}
    if not probs:
        return None, None, "fed:empty"
    current = str(payload.get("current_target") or "")
    current_mid = _mid(current)
    hold = 0.0
    cut = 0.0
    for bucket, pct in probs.items():
        share = float(pct) / 100.0
        mid = _mid(str(bucket))
        if current and bucket == current:
            hold += share
            continue
        if current_mid is not None and mid is not None:
            if mid < current_mid - 1e-9:
                cut += share
            elif abs(mid - current_mid) < 1e-9:
                hold += share
    if hold == 0 and cut == 0:
        return None, None, "fed:unparsed"
    return hold, cut, "fed:implied"


def fetch_fed_probs() -> tuple[float | None, float | None, str]:
    try:
        from cme_fedwatch import get_probabilities  # type: ignore
    except Exception:
        return None, None, "fed:unavailable"
    try:
        data = get_probabilities()
    except Exception as exc:  # noqa: BLE001
        return None, None, f"fed:error:{type(exc).__name__}"
    if not isinstance(data, dict):
        return None, None, "fed:unavailable"
    return summarize_meetings(data)
