from __future__ import annotations


def round_trip_cost_r(
    r_multiple: float,
    taker_fee: float = 0.0005,
    slippage_bps: float = 2.0,
    funding_bars: int = 6,
    avg_funding: float = 0.0001,
    stop_atr_frac: float = 0.01,
) -> float:
    """Convert cash frictions into R units. stop_atr_frac ~ risk per unit price."""
    risk = max(stop_atr_frac, 1e-6)
    fee_r = (2.0 * taker_fee) / risk
    slip_r = (2.0 * slippage_bps / 10_000.0) / risk
    fund_r = (funding_bars * avg_funding) / risk
    return r_multiple - fee_r - slip_r - fund_r
