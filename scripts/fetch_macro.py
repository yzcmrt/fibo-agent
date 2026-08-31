from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from config import load_settings
from data.macro import collect_snapshot, regime_from_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    dominance = {}
    try:
        dominance = orch.dominance.fetch_snapshot()
    except Exception as exc:  # noqa: BLE001
        logging.warning("dominance snapshot failed: %s", exc)
    row = collect_snapshot(orch.store, dominance)
    regime = regime_from_snapshot(row)
    print(json.dumps({"row": row, "regime": regime}, default=str, indent=2))


if __name__ == "__main__":
    main()
