import importlib.util

import pandas as pd

from config import ROOT

_spec = importlib.util.spec_from_file_location("cvdmod", ROOT / "data" / "cvd.py")
cvd = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cvd)


def test_rebase_returns_list():
    rows = [
        {"ts": 1, "buy_vol": 2, "sell_vol": 1, "delta": 1, "cumulative_delta": 1},
        {"ts": 2, "buy_vol": 1, "sell_vol": 0, "delta": 1, "cumulative_delta": 2},
    ]
    out = cvd.rebase_cumulative(rows, last_cum=10)
    assert out[-1]["cumulative_delta"] == 12


def test_attach_asof_sets_available():
    ohlcv = pd.DataFrame(
        {
            "ts": [1000, 2000, 3000, 4000],
            "open": [1, 1, 1, 1],
            "high": [1.1, 1.2, 1.0, 1.3],
            "low": [0.9, 0.9, 0.8, 1.0],
            "close": [1, 1.1, 0.9, 1.2],
            "volume": [1, 1, 1, 1],
        }
    )
    flow = pd.DataFrame(
        {
            "ts": [1000, 3000],
            "cumulative_delta": [5.0, 8.0],
        }
    )
    out = cvd.attach_cvd_features(ohlcv, flow)
    assert out["cvd_available"].iloc[-1] == 1.0
    assert out["cvd_cum"].iloc[1] == 5.0
    assert out["cvd_cum"].iloc[2] == 8.0
