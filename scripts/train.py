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
    timeframe = settings["timeframes"]["primary"]
    min_candles = int(settings["history"]["min_candles_4h"])
    reports = []
    for symbol in settings["symbols"]["perps"]:
        if not orch.hub.has_symbol(exchange, symbol):
            print("skip", symbol)
            continue
        df = orch.ingest_symbol(exchange, symbol, timeframe, min_candles)
        if df.empty:
            print("empty", symbol)
            continue
        result = orch.train(df)
        best = result["best"]
        item = {
            "symbol": symbol,
            "best_params": best["params"] if best else None,
            "best_metrics": best["metrics"] if best else None,
            "indicator_weights": result["weights"],
            "gate": result["gate"],
            "n_labeled": result["n_labeled"],
        }
        reports.append(item)
        print("=== TRAIN", symbol, "===")
        print(json.dumps(item, indent=2))
        if best:
            bt = run_backtest(df, best["params"])
            print("=== BACKTEST", symbol, "===")
            print({k: bt[k] for k in ["n", "wins", "losses", "precision", "avg_r", "max_drawdown_R"] if k in bt})
            from backtest.oos import write_symbol_report

            oos_path = ROOT / "outputs" / "backtest" / f"{symbol.replace('/', '-').replace(':', '-')}.json"
            oos_rep = write_symbol_report(oos_path, symbol, best["params"], df)
            print("=== OOS", symbol, oos_rep.get("oos_reason"), "===")
            analysis = orch.analyze(df, params=best["params"], symbol=symbol)
            if analysis["grids"]:
                out = ROOT / "outputs" / f"{symbol.replace('/', '-').replace(':', '-')}_fib.png"
                render_setup_chart(df, analysis["grids"][-1], out, title=f"{symbol} last swing fib")
                print("chart:", out)
    if not reports:
        raise SystemExit("no candles ingested")


if __name__ == "__main__":
    main()
