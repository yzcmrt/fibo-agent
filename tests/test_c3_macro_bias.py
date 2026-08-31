from analysis.macro_regime import compute_macro_bias


def test_missing_inputs_zero_not_fake():
    assert compute_macro_bias({}) == 0.0
    assert compute_macro_bias({"coinbase_premium_pct": None, "etf_net_flow_usd": None}) == 0.0


def test_positive_premium_and_inflow():
    bias = compute_macro_bias({"coinbase_premium_pct": 0.25, "etf_net_flow_usd": 1_000_000})
    assert bias > 0.5


def test_event_day_dampens():
    base = compute_macro_bias({"coinbase_premium_pct": 0.25, "source_flags": "calendar:quiet"})
    hot = compute_macro_bias({"coinbase_premium_pct": 0.25, "source_flags": '["calendar:FOMC"]'})
    assert abs(hot) < abs(base)
