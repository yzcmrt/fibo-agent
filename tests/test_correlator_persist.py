from learning.correlator import FeatureCorrelator


def test_load_state_returns_numeric_probability():
    corr = FeatureCorrelator()
    corr.load_state(
        weights={"rsi14": 0.4, "ema_trend": 0.2, "vol_z": 0.1, "ret_12": 0.0, "atr_pct": 0.0, "fib_ratio": 0.2, "confluence": 0.1},
        means={"rsi14": (55.0, 45.0)},
    )
    prob = corr.predict_proba({"rsi14": 60.0, "ema_trend": 1.0, "vol_z": 0.2, "fib_ratio": 0.618, "confluence": 70.0})
    assert prob is not None
    assert 0.0 <= prob <= 1.0
