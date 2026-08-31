from __future__ import annotations

from typing import Any

import pandas as pd


def candles_payload(df: pd.DataFrame, limit: int = 180) -> list[dict[str, float]]:
    if df is None or df.empty:
        return []
    work = df.tail(limit)
    out = []
    for ts, row in work.iterrows():
        if hasattr(ts, "timestamp"):
            t = int(ts.timestamp())
        else:
            t = int(pd.Timestamp(ts).timestamp())
        out.append(
            {
                "time": t,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
            }
        )
    return out


def spark_payload(df: pd.DataFrame, column: str = "cumulative_delta", limit: int = 80) -> list[float]:
    if df is None or df.empty or column not in df.columns:
        return []
    return [float(v) if v == v else 0.0 for v in df[column].tail(limit).tolist()]


def fills_by_venue(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"okx": [], "bybit": [], "other": []}
    for row in rows:
        venue = str(row.get("venue") or "other").lower()
        key = venue if venue in grouped else "other"
        grouped[key].append(row)
    return grouped
