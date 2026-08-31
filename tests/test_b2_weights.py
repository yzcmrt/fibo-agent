from signals.confluence import normalize_weights


def test_missing_cvd_zeroed_and_renormalized():
    weights = {
        "fib_proximity": 0.20,
        "cvd_bias": 0.08,
        "htf_alignment": 0.13,
        "regime": 0.09,
    }
    used = normalize_weights(weights, {"cvd_bias": False})
    assert "cvd_bias" not in used
    assert abs(sum(used.values()) - 1.0) < 1e-9
    assert used["fib_proximity"] > 0.20


def test_all_available_keeps_sum():
    weights = {"a": 0.4, "b": 0.6}
    used = normalize_weights(weights, {"a": True, "b": True})
    assert abs(sum(used.values()) - 1.0) < 1e-9
