from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = load_settings()
    if not settings.get("intraday", {}).get("enabled"):
        logging.info("intraday worker disabled (settings.intraday.enabled=false)")
        return
    logging.info("intraday enabled — 5m/15m tarama henüz ayrı backfill ister")


if __name__ == "__main__":
    main()
