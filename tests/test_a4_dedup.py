from alerts.dedup import SignalDeduper, notify_setup, signal_key


def test_same_key_blocked_within_cooldown():
    d = SignalDeduper(cooldown_s=8 * 3600)
    key = signal_key("ETH/USDT:USDT", "4h", "up", 2491.0, 72.0)
    assert d.allow(key, now_ms=1_000_000)
    assert d.allow(key, now_ms=1_000_000 + 60_000) is False
    assert d.allow(key, now_ms=1_000_000 + 9 * 3600 * 1000) is True


def test_notify_setup_calls_sender_once():
    sent = []
    d = SignalDeduper(cooldown_s=100)
    kwargs = dict(
        text="hello",
        symbol="SOL/USDT:USDT",
        timeframe="4h",
        direction="up",
        key_price=150.12,
        score=71,
        deduper=d,
    )
    assert notify_setup(**kwargs, sender=lambda t: sent.append(t) or True)
    assert notify_setup(**kwargs, sender=lambda t: sent.append(t) or True) is False
    assert sent == ["hello"]
