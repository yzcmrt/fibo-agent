from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.engine import run_backtest
from backtest.split import split_insample_oos
from learning.trainer import walk_forward_metrics


def write_symbol_report(
    path: Path,
    symbol: str,
    params: dict[str, Any],
    df: pd.DataFrame,
) -> dict[str, Any]:
    parts = split_insample_oos(df)
    wf = walk_forward_metrics(parts["in_sample"], params) if len(parts["in_sample"]) else {}
    oos_bt = run_backtest(parts["oos"], params, symbol=symbol) if len(parts["oos"]) else {}
    ins_bt = run_backtest(parts["in_sample"], params, symbol=symbol) if len(parts["in_sample"]) else {}
    report = {
        "symbol": symbol,
        "oos_reason": parts["reason"],
        "oos_short": parts["oos_short"],
        "walk_forward": {k: wf.get(k) for k in ("precision", "avg_r", "n_signals", "fitness") if wf},
        "in_sample_net": {k: ins_bt.get(k) for k in ("n", "precision", "net_precision", "avg_r", "net_avg_r") if ins_bt},
        "oos_net": {k: oos_bt.get(k) for k in ("n", "precision", "net_precision", "avg_r", "net_avg_r") if oos_bt},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report
