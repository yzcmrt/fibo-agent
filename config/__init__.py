from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


ROOT = Path(__file__).resolve().parents[1]


def load_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or (ROOT / "config" / "settings.yaml")
    with cfg_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
