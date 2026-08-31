from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from config import load_settings
from learning.forward import forward_stats, resolve_open


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    for symbol in settings["symbols"]["perps"]:
        if not orch.hub.has_symbol(exchange, symbol):
            continue
        df = orch.ingest_symbol(exchange, symbol, "4h", 200)
        n = resolve_open(orch.store, symbol, df)
        print(symbol, "resolved", n)
    print(json.dumps(forward_stats(orch.store), indent=2))


if __name__ == "__main__":
    main()
