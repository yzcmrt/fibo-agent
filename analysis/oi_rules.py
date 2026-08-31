from __future__ import annotations


def label_oi_price(price_ret: float, oi_ret: float, eps: float = 1e-9) -> str:
    if abs(price_ret) <= eps or abs(oi_ret) <= eps:
        return "flat"
    if price_ret > 0 and oi_ret > 0:
        return "new_long"
    if price_ret < 0 and oi_ret > 0:
        return "new_short"
    if price_ret > 0 and oi_ret < 0:
        return "short_cover"
    return "long_liq"


def encode_oi_rule(label: str) -> float:
    return {
        "new_long": 1.0,
        "new_short": -1.0,
        "short_cover": 0.5,
        "long_liq": -0.5,
        "flat": 0.0,
    }.get(label, 0.0)


def funding_roc(current: float | None, previous: float | None) -> float:
    if current is None or previous is None:
        return 0.0
    return float(current) - float(previous)
