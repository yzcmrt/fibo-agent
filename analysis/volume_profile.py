from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VolumeProfile:
    poc: float
    vah: float
    val: float
    bins: int


def volume_profile(df: pd.DataFrame, lookback: int = 120, bins: int = 40, va_pct: float = 0.70) -> VolumeProfile | None:
    window = df.tail(lookback)
    if window.empty:
        return None
    prices = ((window["high"] + window["low"] + window["close"]) / 3.0).to_numpy(dtype=float)
    vols = window["volume"].to_numpy(dtype=float)
    hist, edges = np.histogram(prices, bins=bins, weights=vols)
    if hist.sum() <= 0:
        return None
    poc_idx = int(hist.argmax())
    poc = float((edges[poc_idx] + edges[poc_idx + 1]) / 2.0)
    target = hist.sum() * va_pct
    order = np.argsort(hist)[::-1]
    running = 0.0
    selected = set()
    for idx in order:
        selected.add(int(idx))
        running += float(hist[idx])
        if running >= target:
            break
    sel = sorted(selected)
    val = float(edges[sel[0]])
    vah = float(edges[sel[-1] + 1])
    return VolumeProfile(poc=poc, vah=vah, val=val, bins=bins)
