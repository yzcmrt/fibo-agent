from datetime import datetime, timezone

import pandas as pd

from analysis.features import build_feature_row
from analysis.indicators import add_indicators


def test_build_feature_row_has_canonical_keys():
    start = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    px = 100.0
    for i in range(60):
        px += 0.2
        rows.append(
            {
                "ts": start + i * 3600_000,
                "open": px,
                "high": px + 1,
                "low": px - 1,
                "close": px,
                "volume": 10 + i,
            }
        )
    df = add_indicators(pd.DataFrame(rows))
    feats = build_feature_row(df, len(df) - 1, origin_mode="wick", macro_bias=0.2)
    for key in ("rsi14", "bb_pct", "ema20_slope", "atr_pct", "origin_is_wick", "macro_bias", "channel_position"):
        assert key in feats
    assert feats["origin_is_wick"] == 1.0
    assert feats["macro_bias"] == 0.2
