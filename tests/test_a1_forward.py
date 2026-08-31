import importlib.util
from datetime import datetime, timezone

import pandas as pd

import json as jsonlib

from analysis.fibonacci import build_fib_from_leg
from analysis.indicators import add_indicators
from analysis.pivots import Pivot
from config import ROOT

_spec = importlib.util.spec_from_file_location("fwd", ROOT / "learning" / "forward.py")
fwd = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fwd)


def _df() -> pd.DataFrame:
    n = 80
    rows = []
    price = 100.0
    start = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    step = 4 * 3600 * 1000
    for i in range(n):
        if i < 10:
            price = 100 + i
        elif i < 25:
            price = 110 - (i - 10) * 0.4
        else:
            price = 104 + (i - 25) * 0.35
        rows.append(
            {
                "ts": start + i * step,
                "open": price,
                "high": price + 0.8,
                "low": price - 0.8,
                "close": price,
                "volume": 10.0,
            }
        )
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts")


def test_payload_roundtrip_uses_label_fib_hold():
    df = add_indicators(_df())
    ts0 = df.index[5]
    ts1 = df.index[12]
    start = Pivot(5, ts0, float(df["low"].iloc[5]), "low", "pct", 0.03)
    end = Pivot(12, ts1, float(df["high"].iloc[12]), "high", "pct", 0.03)
    grid = build_fib_from_leg(start, end)
    payload = jsonlib.loads(fwd.dump_grid(grid, 0.618))
    rebuilt = fwd.grid_from_payload(df, payload)
    assert rebuilt is not None
    assert rebuilt.direction == grid.direction
    direct = fwd.label_fib_hold(df, grid, key_ratio=0.618, horizon_bars=30)
    via = fwd.label_fib_hold(df, rebuilt, key_ratio=0.618, horizon_bars=30)
    assert via.note == direct.note
    assert via.success == direct.success


def test_open_notes_not_treated_as_done():
    assert "no_touch" in fwd.OPEN_NOTES
    assert "no_forward_bars" in fwd.OPEN_NOTES
