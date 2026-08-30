from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from analysis.pivots import Pivot


@dataclass
class SRZone:
    low: float
    high: float
    mid: float
    touches: int
    score: float


def cluster_sr(pivots: list[Pivot], cluster_pct: float = 0.006, min_touches: int = 3) -> list[SRZone]:
    if not pivots:
        return []
    prices = np.array(sorted(p.price for p in pivots), dtype=float)
    zones: list[SRZone] = []
    used = np.zeros(len(prices), dtype=bool)
    for i, price in enumerate(prices):
        if used[i]:
            continue
        band = price * cluster_pct
        mask = np.abs(prices - price) <= band
        used |= mask
        cluster = prices[mask]
        if len(cluster) < min_touches:
            continue
        low, high = float(cluster.min()), float(cluster.max())
        mid = float(cluster.mean())
        score = min(100.0, 20.0 * len(cluster) + 10.0)
        zones.append(SRZone(low=low, high=high, mid=mid, touches=int(len(cluster)), score=score))
    return sorted(zones, key=lambda z: z.score, reverse=True)
