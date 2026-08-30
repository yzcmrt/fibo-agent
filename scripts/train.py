from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from alerts.chart_renderer import render_setup_chart
from backtest.engine import run_backtest
from config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    exchange = settings["exchanges"]["primary"]
    if exchange not in orch.hub.available():
        exchange = orch.hub.available()[0]
    symbol = settings["symbols"]["perps"][0]
    timeframe = settings["timeframes"]["primary"]
    min_candles = int(settings["history"]["min_candles_4h"])
    df = orch.ingest_symbol(exchange, symbol, timeframe, min_candles)
    if df.empty:
        raise SystemExit("no candles ingested")

    result = orch.train(df)
    best = result["best"]
    print("=== TRAIN REPORT ===")
    print(json.dumps(
        {
            "best_params": best["params"] if best else None,
            "best_metrics": best["metrics"] if best else None,
            "history": result["history"],
            "indicator_weights": result["weights"],
            "gate": result["gate"],
            "n_labeled": result["n_labeled"],
        },
        indent=2,
    ))
    if best:
        bt = run_backtest(df, best["params"])
        print("=== BACKTEST ===")
        print({k: bt[k] for k in ["n", "wins", "losses", "precision", "avg_r", "max_drawdown_R"]})
        analysis = orch.analyze(df, params=best["params"])
        if analysis["grids"]:
            out = ROOT / "outputs" / f"{symbol.replace('/', '-').replace(':', '-')}_fib.png"
            render_setup_chart(df, analysis["grids"][-1], out, title=f"{symbol} last swing fib")
            print("chart:", out)


if __name__ == "__main__":
    main()
