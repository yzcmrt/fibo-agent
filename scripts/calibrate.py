from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.calibrate import calibrate_all, load_references
from agents.orchestra import AgentOrchestra
from config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    settings["database"]["url"] = "sqlite:////tmp/fibo_agent.db"
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    refs = load_references()
    frames = {}
    symbols = {d["symbol"] for d in refs.get("drawings", [])}
    for symbol in symbols:
        if not orch.hub.has_symbol(exchange, symbol):
            print("missing", exchange, symbol)
            continue
        frames[symbol] = orch.ingest_symbol(exchange, symbol, "4h", 2000)
        print(symbol, "bars", len(frames[symbol]))
    report = calibrate_all(frames)
    slim = []
    for item in report["reports"]:
        if "best" in item:
            slim.append(item["best"])
        else:
            slim.append(item)
    print(json.dumps({"style": report["style"], "best_matches": slim}, indent=2))


if __name__ == "__main__":
    main()
