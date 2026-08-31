from analysis.macro_regime import classify_regime


def test_regime_risk_off_usdt():
    raw = classify_regime(7.2, 55.0, usdt_slope=0.1)
    assert raw["label"] == "risk_off"
    assert raw["alt_bias"] < 0


def test_regime_risk_on_low_usdt():
    raw = classify_regime(4.0, 50.0, usdt_slope=-0.08)
    assert raw["label"] == "risk_on"
    assert raw["alt_bias"] > 0
