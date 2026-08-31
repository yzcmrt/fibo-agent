from __future__ import annotations

from typing import Any

import pandas as pd

from backtest.costs import round_trip_cost_r
from learning.trainer import evaluate_genome


def run_backtest(
    df: pd.DataFrame,
    params: dict[str, Any],
    taker_fee: float = 0.0005,
    slippage_bps: float = 2.0,
    avg_funding: float = 0.0001,
    symbol: str | None = None,
) -> dict[str, Any]:
    metrics, rows, labels = evaluate_genome(df, params)
    wins = sum(labels)
    n = len(labels)
    losses = n - wins
    gross_rs = [float(r.get("_r", 1.0 if y else -1.0)) for r, y in zip(rows, labels)]
    if len(gross_rs) != n:
        gross_rs = [1.0 if y else -1.0 for y in labels]
    net_rs = [
        round_trip_cost_r(r, taker_fee=taker_fee, slippage_bps=slippage_bps, avg_funding=avg_funding)
        for r in gross_rs
    ]
    equity = []
    net_equity = []
    curve = 0.0
    net_curve = 0.0
    peak = 0.0
    net_peak = 0.0
    max_dd = 0.0
    net_dd = 0.0
    for g, net in zip(gross_rs, net_rs):
        curve += g
        net_curve += net
        equity.append(curve)
        net_equity.append(net_curve)
        peak = max(peak, curve)
        net_peak = max(net_peak, net_curve)
        max_dd = min(max_dd, curve - peak)
        net_dd = min(net_dd, net_curve - net_peak)
    precision = wins / n if n else 0.0
    net_wins = sum(1 for r in net_rs if r > 0)
    return {
        "symbol": symbol,
        "n": n,
        "wins": wins,
        "losses": losses,
        "precision": precision,
        "net_precision": net_wins / n if n else 0.0,
        "avg_r": (sum(gross_rs) / n) if n else 0.0,
        "net_avg_r": (sum(net_rs) / n) if n else 0.0,
        "max_drawdown_R": max_dd,
        "net_max_drawdown_R": net_dd,
        "cost_drag_R": ((sum(gross_rs) - sum(net_rs)) / n) if n else 0.0,
        "equity": equity,
        "net_equity": net_equity,
        "metrics": metrics,
    }


def run_backtest_many(frames: dict[str, pd.DataFrame], params: dict[str, Any], **cost) -> dict[str, Any]:
    parts = {sym: run_backtest(df, params, symbol=sym, **cost) for sym, df in frames.items() if df is not None and not df.empty}
    return {"by_symbol": parts, "symbols": list(parts)}
