from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from config import load_settings
from data.cvd import CvdCollector

SYMBOLS = ["ETH/USDT:USDT", "HYPE/USDT:USDT", "SOL/USDT:USDT", "SUI/USDT:USDT", "BTC/USDT:USDT"]


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    collector = CvdCollector(orch.hub, orch.store)
    for symbol in SYMBOLS:
        n = collector.ingest_bar(exchange, symbol, "4h", market="swap")
        print(symbol, "rows", n)


if __name__ == "__main__":
    main()
