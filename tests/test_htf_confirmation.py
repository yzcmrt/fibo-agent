from datetime import datetime, timezone

from analysis.fibonacci import FibGrid
from analysis.pivots import Pivot
from config import load_settings
from signals.confluence import score_setup


def _grid() -> FibGrid:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    start = Pivot(0, ts, 100.0, "low", "pct", 0.05)
    end = Pivot(10, ts, 140.0, "high", "pct", 0.05)
    return FibGrid(
        start=start,
        end=end,
        direction="up",
        levels={0.0: 140.0, 0.5: 120.0, 0.618: 115.28, 1.0: 100.0},
        extensions={1.618: 164.72},
    )


def _score(htf_bias: float) -> float:
    weights = load_settings()["confluence"]["weights"]
    raw = score_setup(
        price=115.3,
        grid=_grid(),
        zones=[],
        lines=[],
        profile=None,
        regime={"alt_bias": 0.0},
        model_prob=None,
        atr=2.0,
        weights=weights,
        bar_index=10,
        htf_bias=htf_bias,
    )
    return raw["score"]


def test_htf_conflict_drops_score_at_least_15_points():
    aligned = _score(1.0)
    opposed = _score(-1.0)
    assert aligned - opposed >= 15.0
    assert opposed <= 60.0


def test_weights_sum_to_one():
    weights = load_settings()["confluence"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert "htf_alignment" in weights
