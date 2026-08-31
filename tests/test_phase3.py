import pandas as pd

from analysis.indicators import add_indicators, snapshot_features
from config import ROOT, load_settings


def test_snapshot_has_bollinger_fields():
    n = 80
    close = [100 + i * 0.2 for i in range(n)]
    df = pd.DataFrame(
        {
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000 + (i % 7) * 10 for i in range(n)],
        }
    )
    work = add_indicators(df)
    feats = snapshot_features(work, len(work) - 1)
    assert "bb_pct" in feats
    assert "bb_width" in feats
    assert "conviction" in feats
    assert work["bb_upper"].iloc[-1] > work["bb_mid"].iloc[-1] > work["bb_lower"].iloc[-1]


def test_hold_features_include_bb():
    text = (ROOT / "learning" / "hold_miner.py").read_text(encoding="utf-8")
    assert '"bb_pct"' in text
    assert '"bb_width"' in text


def test_weights_still_sum_to_one():
    weights = load_settings()["confluence"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert "bb_position" in weights
