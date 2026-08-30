from __future__ import annotations

import pandas as pd

from analysis.pivots import detect_pivots


def _ema_slope_bias(df: pd.DataFrame) -> float:
    if df is None or df.empty or "close" not in df.columns:
        return 0.0
    close = df["close"].astype(float)
    if len(close) < 55:
        return 0.0
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    last20 = float(ema20.iloc[-1])
    last50 = float(ema50.iloc[-1])
    prev20 = float(ema20.iloc[-5]) if len(ema20) >= 5 else last20
    if last50 == 0:
        return 0.0
    spread = (last20 - last50) / abs(last50)
    slope = (last20 - prev20) / abs(last50)
    raw = 4.0 * spread + 8.0 * slope
    return max(-1.0, min(1.0, raw))


def _structure_bias(df: pd.DataFrame, threshold: float = 0.04) -> float:
    if df is None or df.empty or len(df) < 30:
        return 0.0
    pivots = detect_pivots(df, method="pct", threshold=threshold)
    highs = [p for p in pivots if p.kind == "high"]
    lows = [p for p in pivots if p.kind == "low"]
    if len(highs) < 2 or len(lows) < 2:
        return 0.0
    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    lh = highs[-1].price < highs[-2].price
    ll = lows[-1].price < lows[-2].price
    if hh and hl:
        return 1.0
    if lh and ll:
        return -1.0
    if hh or hl:
        return 0.35
    if lh or ll:
        return -0.35
    return 0.0


def timeframe_bias(df: pd.DataFrame, threshold: float = 0.04) -> float:
    ema = _ema_slope_bias(df)
    struct = _structure_bias(df, threshold=threshold)
    return max(-1.0, min(1.0, 0.55 * ema + 0.45 * struct))


def combine_htf_bias(daily: pd.DataFrame | None, weekly: pd.DataFrame | None) -> float:
    parts = []
    if daily is not None and not daily.empty:
        parts.append((0.6, timeframe_bias(daily, threshold=0.05)))
    if weekly is not None and not weekly.empty:
        parts.append((0.4, timeframe_bias(weekly, threshold=0.08)))
    if not parts:
        return 0.0
    num = sum(w * b for w, b in parts)
    den = sum(w for w, _ in parts)
    return max(-1.0, min(1.0, num / den))


def alignment(direction: str, htf_bias: float) -> float:
    signed = htf_bias if direction == "up" else -htf_bias
    return max(-1.0, min(1.0, signed))
