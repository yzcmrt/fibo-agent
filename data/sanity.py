from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def sanity_check(df: pd.DataFrame, jump_pct: float = 0.50) -> dict[str, float | int | bool]:
    """Flag missing candles and pathological single-bar jumps."""
    if df.empty:
        return {"ok": False, "rows": 0, "gaps": 0, "jumps": 0}
    close = df["close"].astype(float)
    ret = close.pct_change().abs()
    jumps = int((ret > jump_pct).sum())
    deltas = df.index.to_series().diff().dropna()
    if deltas.empty:
        gaps = 0
    else:
        median = deltas.median()
        gaps = int((deltas > median * 2.5).sum())
    ok = jumps == 0 and gaps < max(5, int(len(df) * 0.01))
    report = {"ok": ok, "rows": int(len(df)), "gaps": gaps, "jumps": jumps}
    if not ok:
        logger.warning("sanity anomalies: %s", report)
    return report
