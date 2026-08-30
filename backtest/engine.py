from __future__ import annotations

from typing import Any

import pandas as pd

from learning.trainer import evaluate_genome


def run_backtest(df: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    metrics, rows, labels = evaluate_genome(df, params)
    wins = sum(labels)
    n = len(labels)
    losses = n - wins
    equity = []
    curve = 0.0
    peak = 0.0
    max_dd = 0.0
    for y in labels:
        curve += 1.0 if y == 1 else -1.0
        equity.append(curve)
        peak = max(peak, curve)
        max_dd = min(max_dd, curve - peak)
    precision = wins / n if n else 0.0
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "precision": precision,
        "avg_r": metrics["avg_r"],
        "max_drawdown_R": max_dd,
        "equity": equity,
        "metrics": metrics,
    }
