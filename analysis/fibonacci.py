from __future__ import annotations

from dataclasses import dataclass, field

from analysis.pivots import Pivot


RETRACEMENTS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
EXTENSIONS = (1.272, 1.618, 2.0, 2.618, 3.618, 4.236)


@dataclass
class FibGrid:
    start: Pivot
    end: Pivot
    direction: str  # "up" or "down"
    levels: dict[float, float] = field(default_factory=dict)
    extensions: dict[float, float] = field(default_factory=dict)

    @property
    def range(self) -> float:
        return abs(self.end.price - self.start.price)

    def nearest_retracement(self, price: float) -> tuple[float, float, float]:
        """Return (ratio, level_price, abs_distance)."""
        best = (0.0, self.end.price, abs(price - self.end.price))
        for ratio, lvl in self.levels.items():
            dist = abs(price - lvl)
            if dist < best[2]:
                best = (ratio, lvl, dist)
        return best


def build_fib_from_leg(
    start: Pivot,
    end: Pivot,
    retracements: tuple[float, ...] = RETRACEMENTS,
    extensions: tuple[float, ...] = EXTENSIONS,
) -> FibGrid:
    direction = "up" if end.price > start.price else "down"
    span = end.price - start.price
    levels = {r: end.price - span * r for r in retracements}
    ext = {e: end.price + span * (e - 1.0) for e in extensions}
    return FibGrid(start=start, end=end, direction=direction, levels=levels, extensions=ext)


def grids_from_pivots(pivots: list[Pivot], last_n_legs: int = 8) -> list[FibGrid]:
    if len(pivots) < 2:
        return []
    grids: list[FibGrid] = []
    pairs = list(zip(pivots[:-1], pivots[1:]))
    for start, end in pairs[-last_n_legs:]:
        if start.kind == end.kind:
            continue
        grids.append(build_fib_from_leg(start, end))
    return grids
