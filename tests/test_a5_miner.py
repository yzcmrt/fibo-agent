from learning.hold_miner import key_ratios_for_symbol


def test_btc_has_no_extension():
    ratios = key_ratios_for_symbol("BTC/USDT:USDT")
    assert 1.618 not in ratios
    assert 0.618 in ratios


def test_eth_keeps_extension():
    ratios = key_ratios_for_symbol("ETH/USDT:USDT")
    assert 1.618 in ratios
