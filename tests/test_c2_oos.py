from datetime import datetime, timezone

import pandas as pd

from backtest.split import split_insample_oos


def test_split_marks_short_when_history_thin():
    idx = pd.date_range("2026-07-01", periods=40, freq="4h", tz="UTC")
    df = pd.DataFrame({"close": range(40)}, index=idx)
    parts = split_insample_oos(df, months=12)
    assert parts["oos_short"] is True
    assert "kısa" in parts["reason"] or "short" in parts["reason"].lower() or "OOS" in parts["reason"]


def test_split_ok_on_long_history():
    idx = pd.date_range("2023-01-01", periods=5000, freq="4h", tz="UTC")
    df = pd.DataFrame({"close": range(5000)}, index=idx)
    parts = split_insample_oos(df, months=12)
    assert parts["oos_short"] is False
    assert len(parts["oos"]) > 80
    assert len(parts["in_sample"]) > 80
