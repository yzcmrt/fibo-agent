import importlib.util

from config import ROOT

_spec = importlib.util.spec_from_file_location("wtuner", ROOT / "learning" / "weight_tuner.py")
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mod)
cohens_d = mod.cohens_d
feature_delta_table = mod.feature_delta_table
propose_weights = mod.propose_weights


def test_cohens_d_separates():
    hold = [0.8, 0.9, 0.85, 0.88, 0.92]
    fail = [0.1, 0.2, 0.15, 0.18, 0.12]
    assert cohens_d(hold, fail) > 0.4


def test_propose_weights_cuts_weak_and_sums_to_one():
    current = {
        "fib_proximity": 0.20,
        "sr_overlap": 0.13,
        "trendline": 0.11,
        "volume_oi": 0.10,
        "regime": 0.09,
        "indicator_model": 0.08,
        "htf_alignment": 0.13,
        "bb_position": 0.08,
        "cvd_bias": 0.08,
    }
    holds = [{"bb_pct": 0.9, "cvd_slope": 0.01, "htf_alignment": 0.9} for _ in range(8)]
    fails = [{"bb_pct": 0.1, "cvd_slope": 0.00, "htf_alignment": -0.8} for _ in range(8)]
    deltas = feature_delta_table(holds, fails, ["bb_pct", "cvd_slope", "htf_alignment"])
    out = propose_weights(current, deltas)
    assert abs(sum(out["weights"].values()) - 1.0) < 1e-6
    assert "std_delta" in deltas["bb_pct"]
    assert out["weights"]["htf_alignment"] >= 0.06
