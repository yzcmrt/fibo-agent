from datetime import datetime, timezone

import pandas as pd

from dashboard.series import candles_payload, fills_by_venue, spark_payload


def test_candles_and_spark():
    idx = pd.date_range(datetime(2026, 1, 1, tzinfo=timezone.utc), periods=3, freq="4h")
    df = pd.DataFrame(
        {"open": [1, 2, 3], "high": [2, 3, 4], "low": [0.5, 1, 2], "close": [1.5, 2.5, 3.5]},
        index=idx,
    )
    candles = candles_payload(df)
    assert len(candles) == 3
    assert "time" in candles[0] and "close" in candles[0]
    spark = spark_payload(pd.DataFrame({"cumulative_delta": [1.0, 2.0, 3.0]}))
    assert spark == [1.0, 2.0, 3.0]


def test_fills_split_venues():
    grouped = fills_by_venue(
        [
            {"venue": "okx", "symbol": "ETH/USDT:USDT"},
            {"venue": "bybit", "symbol": "BTC/USDT:USDT"},
        ]
    )
    assert len(grouped["okx"]) == 1
    assert len(grouped["bybit"]) == 1
