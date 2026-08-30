from __future__ import annotations

import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    vol = out["volume"].astype(float)
    prev = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=14).mean()
    out["rsi14"] = _rsi(close, 14)
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema55"] = close.ewm(span=55, adjust=False).mean()
    out["ema_trend"] = (out["ema21"] - out["ema55"]) / out["ema55"]
    out["vol_z"] = (vol - vol.rolling(50, min_periods=20).mean()) / vol.rolling(50, min_periods=20).std()
    out["ret_1"] = close.pct_change()
    out["ret_12"] = close.pct_change(12)
    return out


def snapshot_features(df: pd.DataFrame, idx: int) -> dict[str, float]:
    row = df.iloc[idx]
    keys = ["rsi14", "atr14", "ema_trend", "vol_z", "ret_1", "ret_12"]
    feats: dict[str, float] = {}
    for k in keys:
        val = row.get(k)
        try:
            feats[k] = float(val) if val == val else 0.0
        except Exception:  # noqa: BLE001
            feats[k] = 0.0
    feats["close"] = float(row["close"])
    return feats
