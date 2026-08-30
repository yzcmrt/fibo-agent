from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.fibonacci import grids_from_pivots
from analysis.origins import rebase_pivot
from analysis.pivots import detect_pivots
from agents.orchestra import AgentOrchestra
from config import load_settings
from learning.hold_miner import mine_hold_correlations
from learning.memory import LearningMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


SYMBOLS = ["ETH/USDT:USDT", "HYPE/USDT:USDT", "SOL/USDT:USDT", "SUI/USDT:USDT", "BTC/USDT:USDT"]
TFS = ["1d", "4h"]


def persist_drawings(orch: AgentOrchestra, symbol: str, timeframe: str, df) -> int:
    pivots = detect_pivots(df, method="pct", threshold=0.05 if timeframe == "4h" else 0.08)
    grids = grids_from_pivots([rebase_pivot(df, p, "wick") for p in pivots], last_n_legs=4)
    n = 0
    for grid in grids[-2:]:
        orch.store.execute(
            """
            INSERT INTO live_drawings (
                symbol, timeframe, direction, origin_mode, swing_low, swing_high,
                levels_json, extensions_json, confluence, status, created_ts
            ) VALUES (
                :symbol, :timeframe, :direction, :origin_mode, :swing_low, :swing_high,
                :levels_json, :extensions_json, :confluence, :status,
                CAST(strftime('%s','now') AS INTEGER)*1000
            )
            """,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": grid.direction,
                "origin_mode": "wick",
                "swing_low": min(grid.start.price, grid.end.price),
                "swing_high": max(grid.start.price, grid.end.price),
                "levels_json": json.dumps({str(k): v for k, v in grid.levels.items()}),
                "extensions_json": json.dumps({str(k): v for k, v in grid.extensions.items()}),
                "confluence": None,
                "status": "pending",
            },
        )
        n += 1
    return n


def write_report(orch: AgentOrchestra, kind: str, title: str, body: str) -> None:
    orch.store.execute(
        """
        INSERT INTO reports (kind, title, body, created_ts)
        VALUES (:kind, :title, :body, CAST(strftime('%s','now') AS INTEGER)*1000)
        """,
        {"kind": kind, "title": title, "body": body},
    )


def cycle_once(min_candles: int = 2200) -> None:
    settings = load_settings()
    orch = AgentOrchestra(settings)
    exchange = "okx" if "okx" in orch.hub.available() else orch.hub.available()[0]
    drawn = 0
    notes = []
    for symbol in SYMBOLS:
        if not orch.hub.has_symbol(exchange, symbol):
            notes.append(f"skip {symbol}")
            continue
        for tf in TFS:
            need = min_candles if tf == "4h" else max(800, min_candles // 6)
            df = orch.ingest_symbol(exchange, symbol, tf, need)
            if df.empty:
                continue
            drawn += persist_drawings(orch, symbol, tf, df)
            if tf == "4h" and symbol == "ETH/USDT:USDT":
                mined = mine_hold_correlations(df, origin_mode="wick")
                LearningMemory(orch.store).log_phase("mine", json.dumps(mined["rules"]))
                notes.append(f"ETH miner hold={mined['n_hold']} fail={mined['n_fail']}")
                if mined["rules"]:
                    write_report(orch, "learn", "ETH hold korelasyonları", "\n".join(mined["rules"]))
    write_report(orch, "cycle", "Worker turu", f"{drawn} yeni çizim. " + "; ".join(notes))
    logging.info("cycle done drawings=%s", drawn)


def main() -> None:
    loop = "--loop" in sys.argv
    interval = 4 * 3600
    cycle_once()
    while loop:
        logging.info("sleep %ss", interval)
        time.sleep(interval)
        cycle_once()


if __name__ == "__main__":
    main()
