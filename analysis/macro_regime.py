from __future__ import annotations

from typing import Any


def classify_regime(usdt_d: float | None, btc_d: float | None, usdt_slope: float = 0.0) -> dict[str, Any]:
    """Rule-based risk-on / risk-off from stablecoin and BTC dominance."""
    usdt = float(usdt_d or 0.0)
    btc = float(btc_d or 0.0)
    if usdt_slope > 0.05 or usdt >= 6.5:
        label = "risk_off"
        alt_bias = -1.0
    elif usdt_slope < -0.05 or usdt <= 4.5:
        label = "risk_on"
        alt_bias = 1.0
    else:
        label = "neutral"
        alt_bias = 0.0
    if btc >= 58:
        btc_regime = "btc_led"
    elif btc <= 48:
        btc_regime = "alt_seasonish"
    else:
        btc_regime = "balanced"
    return {"label": label, "alt_bias": alt_bias, "btc_regime": btc_regime, "usdt_d": usdt, "btc_d": btc}
