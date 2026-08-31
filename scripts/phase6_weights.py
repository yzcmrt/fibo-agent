from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.orchestra import AgentOrchestra
from config import ROOT as CFG_ROOT, load_settings
from learning.hold_miner import mine_hold_correlations


def main() -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    symbol = "ETH/USDT:USDT"
    df = orch.ingest_symbol(exchange, symbol, "4h", 1500)
    daily = orch.ingest_symbol(exchange, symbol, "1d", 400)
    weights = settings["confluence"]["weights"]
    mined = mine_hold_correlations(df, origin_mode="wick", daily=daily, weights=weights)
    body = json.dumps(
        {
            "n_hold": mined["n_hold"],
            "n_fail": mined["n_fail"],
            "feature_delta": mined["feature_delta"],
            "proposed_weights": mined["proposed_weights"],
            "notes": mined["weight_notes"],
        },
        indent=2,
    )
    orch.store.execute(
        """
        INSERT INTO reports (kind, title, body, created_ts)
        VALUES ('learn', 'Faz 6 feature_delta', :body, CAST(strftime('%s','now') AS INTEGER)*1000)
        """,
        {"body": body},
    )
    out = CFG_ROOT / "config" / "weights_measured.yaml"
    out.write_text(
        yaml.safe_dump(
            {
                "confluence": {"weights": mined["proposed_weights"] or weights},
                "notes": mined["weight_notes"],
                "n_hold": mined["n_hold"],
                "n_fail": mined["n_fail"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(body)
    print("wrote", out)


if __name__ == "__main__":
    main()
