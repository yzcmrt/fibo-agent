from analysis.calibrate import math_match_drawing
from analysis.channels import build_channel
from analysis.fibonacci import grid_from_prices
from analysis.pivots import Pivot
from datetime import datetime, timezone


def test_eth_summer26_extension_within_one_percent():
    drawing = {
        "id": "eth_4h_summer26",
        "symbol": "ETH/USDT:USDT",
        "direction": "up",
        "swing_low": 1540.54,
        "swing_high": 2132.86,
        "expected_extensions": {"1.618": 2491.0},
    }
    row = math_match_drawing(drawing)
    assert row["ext_err_pct"]["1.618"] < 1.0
    grid = grid_from_prices(1540.54, 2132.86, "up")
    assert abs(grid.start.price - 1540.54) / 1540.54 < 0.01
    assert abs(grid.end.price - 2132.86) / 2132.86 < 0.01


def test_fib_channel_bands():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    start = Pivot(0, ts, 100.0, "low", "pct", 0.05)
    end = Pivot(10, ts, 140.0, "high", "pct", 0.05)
    ch = build_channel(start, end)
    bands = ch.bands_at(10)
    assert ch.direction == "up"
    assert abs(bands[1.0] - 140.0) < 1e-6
    assert bands[1.618] > bands[1.0] > bands[0.5] > bands[0.0]
