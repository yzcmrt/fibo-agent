import importlib.util

from config import ROOT, load_settings

_spec = importlib.util.spec_from_file_location("cvdmod", ROOT / "data" / "cvd.py")
cvdmod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(cvdmod)
aggregate_trades = cvdmod.aggregate_trades
classify_side = cvdmod.classify_side
cvd_divergence = cvdmod.cvd_divergence
cvd_slope = cvdmod.cvd_slope


def test_tick_rule_and_taker_side():
    assert classify_side({"side": "sell", "price": 10}, 9) == "sell"
    assert classify_side({"price": 11}, 10) == "buy"
    assert classify_side({"price": 9}, 10) == "sell"


def test_aggregate_trades_builds_delta():
    trades = [
        {"timestamp": 1_700_000_000_000, "price": 100, "amount": 2, "side": "buy"},
        {"timestamp": 1_700_000_000_100, "price": 101, "amount": 1, "side": "sell"},
        {"timestamp": 1_700_014_400_000, "price": 102, "amount": 3, "side": "buy"},
    ]
    rows = aggregate_trades(trades, "4h")
    assert len(rows) == 2
    assert rows[0]["delta"] == 1.0
    assert rows[1]["cumulative_delta"] == 4.0


def test_divergence_price_hh_cvd_not():
    assert cvd_divergence([1, 2, 3, 5], [1, 4, 3, 2]) == 1.0
    assert cvd_slope([10, 11, 12, 16], 4) > 0


def test_cvd_weight_present():
    weights = load_settings()["confluence"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert "cvd_bias" in weights
