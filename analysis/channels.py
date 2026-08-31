from __future__ import annotations

from dataclasses import dataclass, field

from analysis.fibonacci import FibGrid
from analysis.pivots import Pivot

CHANNEL_RATIOS = (0.0, 0.5, 1.0, 1.618)


@dataclass
class FibChannel:
    start: Pivot
    end: Pivot
    direction: str
    slope: float
    width: float
    ratios: tuple[float, ...] = CHANNEL_RATIOS
    origin_mode: str = "wick"

    def price_at(self, ratio: float, bar_index: int) -> float:
        base = self.start.price + self.slope * (bar_index - self.start.index)
        return base + self.width * (ratio - 1.0)

    def bands_at(self, bar_index: int) -> dict[float, float]:
        return {r: self.price_at(r, bar_index) for r in self.ratios}


def build_channel(start: Pivot, end: Pivot, origin_mode: str = "wick") -> FibChannel:
    dt = max(end.index - start.index, 1)
    slope = (end.price - start.price) / dt
    width = end.price - start.price
    direction = "up" if end.price > start.price else "down"
    return FibChannel(
        start=start,
        end=end,
        direction=direction,
        slope=slope,
        width=width,
        origin_mode=origin_mode,
    )


def channel_from_grid(grid: FibGrid) -> FibChannel:
    ch = build_channel(grid.start, grid.end, origin_mode=getattr(grid, "origin_mode", "wick"))
    return ch
