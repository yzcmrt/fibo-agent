from analysis.oi_rules import encode_oi_rule, funding_roc, label_oi_price


def test_oi_labels():
    assert label_oi_price(0.02, 0.05) == "new_long"
    assert label_oi_price(-0.02, 0.05) == "new_short"
    assert label_oi_price(0.02, -0.05) == "short_cover"
    assert label_oi_price(-0.02, -0.05) == "long_liq"
    assert encode_oi_rule("new_long") == 1.0


def test_funding_roc():
    assert funding_roc(0.0002, 0.0001) == 0.0001
    assert funding_roc(None, 0.1) == 0.0
