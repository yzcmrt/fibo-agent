from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from config import load_settings
from learning.hold_miner import mine_hold_correlations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    settings["database"]["url"] = "sqlite:////tmp/fibo_agent.db"
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    symbol = "ETH/USDT:USDT"
    df = orch.ingest_symbol(exchange, symbol, "4h", 3000)
    wick = mine_hold_correlations(df, origin_mode="wick")
    close = mine_hold_correlations(df, origin_mode="close")
    print(json.dumps({"wick": wick, "close": close}, indent=2))


if __name__ == "__main__":
    main()
