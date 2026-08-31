from __future__ import annotations

from typing import Any

import pandas as pd


def split_insample_oos(df: pd.DataFrame, months: int = 12) -> dict[str, Any]:
    if df is None or df.empty:
        return {"in_sample": df, "oos": df, "reason": "empty", "oos_short": True}
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        if "ts" in df.columns:
            work = df.copy()
            work["_ts"] = pd.to_datetime(work["ts"], utc=True, errors="coerce")
            work = work.dropna(subset=["_ts"]).set_index("_ts")
            return split_insample_oos(work, months)
        return {"in_sample": df, "oos": df.iloc[0:0], "reason": "no_datetime_index", "oos_short": True}
    last = idx.max()
    cut = last - pd.DateOffset(months=months)
    oos = df[idx >= cut]
    ins = df[idx < cut]
    short = len(oos) < 80 or len(ins) < 80
    reason = "ok" if not short else f"OOS kısa oos_bars={len(oos)} ins_bars={len(ins)}"
    return {"in_sample": ins, "oos": oos, "reason": reason, "oos_short": short, "cut": str(cut)}
