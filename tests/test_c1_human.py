from learning.human_labels import apply_human_overrides


def test_human_fail_overrides_and_is_copied():
    rows = [{"close": 100.0, "rsi14": 40.0}, {"close": 200.0, "rsi14": 70.0}]
    labels = [1, 1]
    reviews = [{"label": "fail", "swing_low": 90.0, "swing_high": 110.0}]
    out_rows, out_labels, hits = apply_human_overrides(rows, labels, reviews, copies=3)
    assert hits == 1
    assert out_labels[0] == 0
    assert out_labels.count(0) == 4
    assert len(out_rows) == 5
