from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_settings
from agents.orchestra import AgentOrchestra

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    print("available exchanges:", orch.hub.available())
    print("unavailable:", orch.hub.unavailable)
    timeframe = settings["timeframes"]["primary"]
    min_candles = int(settings["history"]["min_candles_4h"])
    exchanges = [e for e in settings["exchanges"]["enabled"] if e in orch.hub.available()]
    for exchange in exchanges:
        for symbol in settings["symbols"]["perps"]:
            if not orch.hub.has_symbol(exchange, symbol):
                print(f"skip missing market {exchange} {symbol}")
                continue
            df = orch.ingest_symbol(exchange, symbol, timeframe, min_candles)
            print(f"{exchange} {symbol} {timeframe}: {len(df)} candles")
            if not df.empty:
                print(f"  range {df.index[0]} -> {df.index[-1]} last={df['close'].iloc[-1]}")
    try:
        snap = orch.dominance.fetch_snapshot()
        print("dominance snapshot:", snap)
        print("regime:", orch.dominance.regime_label(snap))
    except Exception as exc:  # noqa: BLE001
        print("dominance snapshot failed:", exc)


if __name__ == "__main__":
    main()
