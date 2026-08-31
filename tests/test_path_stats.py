from datetime import datetime, timezone

import pandas as pd

from analysis.fibonacci import build_fib_from_leg
from analysis.indicators import add_indicators
from analysis.path_stats import dist_to_extreme_now, outcome_path_stats
from analysis.pivots import Pivot


def _df() -> pd.DataFrame:
    start = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    px = 100.0
    for i in range(90):
        if i < 15:
            px = 100 + i
        elif i < 30:
            px = 115 - (i - 15) * 0.6
        else:
            px = 106 + (i - 30) * 0.4
        rows.append(
            {
                "ts": start + i * 4 * 3600 * 1000,
                "open": px,
                "high": px + 1.2,
                "low": px - 1.2,
                "close": px,
                "volume": 8.0,
            }
        )
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return add_indicators(df.set_index("ts"))


def test_live_distance_and_outcome_keys():
    df = _df()
    start = Pivot(5, df.index[5], float(df["low"].iloc[5]), "low", "pct", 0.03)
    end = Pivot(14, df.index[14], float(df["high"].iloc[14]), "high", "pct", 0.03)
    grid = build_fib_from_leg(start, end)
    now = dist_to_extreme_now(float(df["close"].iloc[-1]), grid)
    assert now >= 0
    stats = outcome_path_stats(df, grid, key_ratio=0.618, horizon_bars=40)
    assert set(stats) >= {"pct_run", "dist_to_extreme", "bars_to_ext", "tag_wick"}
    assert stats["bars_to_ext"] >= 0
