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


def compute_macro_bias(row: dict[str, Any] | None) -> float:
    """Premium + ETF sign + event-day dampener. Missing inputs are skipped, not zero-filled as facts."""
    if not row:
        return 0.0
    parts: list[float] = []
    prem = row.get("coinbase_premium_pct")
    flow = row.get("etf_net_flow_usd")
    if prem is not None and prem == prem:
        parts.append(max(-1.0, min(1.0, float(prem) / 0.25)))
    if flow is not None and flow == flow:
        parts.append(1.0 if float(flow) > 0 else -1.0 if float(flow) < 0 else 0.0)
    if not parts:
        return 0.0
    bias = sum(parts) / len(parts)
    flags = str(row.get("source_flags") or "")
    if "calendar:" in flags and "quiet" not in flags:
        bias *= 0.7
    return max(-1.0, min(1.0, bias))
