from __future__ import annotations

from typing import Any

import pandas as pd

from analysis.indicators import add_indicators, snapshot_features


def _slope_extras(df: pd.DataFrame, idx: int) -> dict[str, float]:
    row = df.iloc[idx]
    close = float(row["close"])
    ema50 = float(row["ema55"]) if row.get("ema55") == row.get("ema55") else close
    ema21 = float(row["ema21"]) if row.get("ema21") == row.get("ema21") else close
    prev_ema = float(df["ema21"].iloc[max(0, idx - 3)]) if idx >= 3 else ema21
    return {
        "ema20_slope": (ema21 - prev_ema) / max(abs(prev_ema), 1e-9),
        "close_vs_ema50": (close - ema50) / max(abs(ema50), 1e-9),
        "atr_pct": float(row.get("atr14") or 0.0) / max(close, 1e-9),
    }


def build_feature_row(
    df: pd.DataFrame,
    idx: int,
    *,
    grid: Any | None = None,
    origin_mode: str = "wick",
    daily: pd.DataFrame | None = None,
    htf_bias: float | None = None,
    macro_bias: float = 0.0,
    fib_ratio: float | None = None,
) -> dict[str, float]:
    work = df if "rsi14" in getattr(df, "columns", []) else add_indicators(df)
    idx = max(0, min(int(idx), len(work) - 1))
    feats = snapshot_features(work, idx)
    feats.update(_slope_extras(work, idx))
    feats["origin_is_wick"] = 1.0 if origin_mode == "wick" else 0.0
    feats["macro_bias"] = float(macro_bias)
    feats["cvd_available"] = float(feats.get("cvd_available") or 0.0)
    if htf_bias is None and daily is not None and not daily.empty:
        from analysis.trend_confirmation import timeframe_bias

        htf_bias = timeframe_bias(daily)
    aligned = float(htf_bias or 0.0)
    if grid is not None and getattr(grid, "direction", "up") == "down":
        aligned = -aligned
    feats["htf_alignment"] = aligned
    feats["channel_position"] = 0.5
    if grid is not None:
        try:
            from analysis.channels import channel_from_grid

            bands = channel_from_grid(grid).bands_at(idx)
            width = bands[1.0] - bands[0.0]
            px = float(work["close"].iloc[idx])
            feats["channel_position"] = (px - bands[0.0]) / width if width else 0.5
        except Exception:  # noqa: BLE001
            feats["channel_position"] = 0.5
    if fib_ratio is not None:
        feats["fib_ratio"] = float(fib_ratio)
    return feats


def feature_snapshot(df, idx: int) -> dict[str, float]:
    return build_feature_row(df, idx)
