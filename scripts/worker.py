from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.nested import nested_grids, split_by_origin
from agents.orchestra import AgentOrchestra
from config import load_settings
from data.cvd import CvdCollector, attach_cvd_features
from data.funding_oi import latest_features, persist_snapshot
from alerts.dedup import SignalDeduper, notify_setup
from alerts.telegram import send_signal
from learning.forward import enqueue_forward
from learning.hold_miner import mine_hold_correlations
from learning.memory import LearningMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


SYMBOLS = ["ETH/USDT:USDT", "HYPE/USDT:USDT", "SOL/USDT:USDT", "SUI/USDT:USDT", "BTC/USDT:USDT"]
TFS = ["1d", "4h"]


def persist_drawings(orch: AgentOrchestra, symbol: str, timeframe: str, df) -> int:
    grids = nested_grids(df, orch.settings, last_n_legs=4)
    if "BTC" in symbol.upper():
        for grid in grids:
            grid.extensions = {}
    grouped = split_by_origin(grids)
    chosen = grouped["wick"][-2:] + grouped["close"][-2:]
    n = 0
    for grid in chosen:
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
                "origin_mode": grid.origin_mode,
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
    collector = CvdCollector(orch.hub, orch.store)
    deduper = SignalDeduper(store=orch.store)
    drawn = 0
    notes = []
    for symbol in SYMBOLS:
        if not orch.hub.has_symbol(exchange, symbol):
            notes.append(f"skip {symbol}")
            continue
        frames = {}
        for tf in TFS + ["1w"]:
            if tf == "1w":
                need = 260
            elif tf == "4h":
                need = min_candles
            else:
                need = max(800, min_candles // 6)
            try:
                frames[tf] = orch.ingest_symbol(exchange, symbol, tf, need)
            except Exception as exc:  # noqa: BLE001
                notes.append(f"{symbol} {tf} {exc}")
                frames[tf] = None
        try:
            n_cvd = collector.ingest_bar(exchange, symbol, "4h", market="swap")
            notes.append(f"{symbol} cvd_swap={n_cvd}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{symbol} cvd {exc}")
        spot = symbol.replace(":USDT", "")
        try:
            n_spot = collector.ingest_bar(exchange, spot, "4h", market="spot")
            notes.append(f"{spot} cvd_spot={n_spot}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{spot} cvd_spot {exc}")
        for tf in TFS:
            df = frames.get(tf)
            if df is None or getattr(df, "empty", True):
                continue
            if tf == "4h":
                try:
                    cvd_df = orch.store.load_cvd(exchange, symbol, "swap", "4h")
                    if "ts" not in df.columns and df.index is not None:
                        df = df.copy()
                        df["ts"] = [int(pd_ts.timestamp() * 1000) if hasattr(pd_ts, "timestamp") else int(pd_ts) for pd_ts in df.index]
                    df = attach_cvd_features(df, cvd_df)
                    persist_snapshot(orch.hub, orch.store, exchange, symbol)
                    pret = 0.0
                    if len(df) >= 2:
                        prev_px = float(df["close"].iloc[-2])
                        pret = float(df["close"].iloc[-1]) / prev_px - 1.0 if prev_px else 0.0
                    extra = latest_features(orch.store, exchange, symbol, pret)
                    for key, value in extra.items():
                        df[key] = value
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"{symbol} cvd_join {exc}")
            drawn += persist_drawings(orch, symbol, tf, df)
            if tf == "4h":
                analysis = orch.analyze(
                    df,
                    daily=frames.get("1d"),
                    weekly=frames.get("1w"),
                    symbol=symbol,
                )
                notes.append(f"{symbol} htf={analysis.get('htf_bias'):.2f}")
                for item in analysis.get("scored") or []:
                    raw = item.get("score") or {}
                    if float(raw.get("score") or 0) >= float(orch.settings["confluence"].get("signal_threshold", 70)):
                        enqueue_forward(
                            orch.store,
                            symbol,
                            tf,
                            raw.get("direction") or "up",
                            float(raw.get("nearest_price") or 0),
                            grid=item.get("grid"),
                            key_ratio=float(raw.get("nearest_ratio") or 0.618),
                        )
                        if orch.settings.get("alerts", {}).get("enabled"):
                            notify_setup(
                                text=(
                                    f"{symbol} {tf} score={raw.get('score'):.1f} "
                                    f"{raw.get('direction')} {raw.get('nearest_ratio')} @ {raw.get('nearest_price')}"
                                ),
                                symbol=symbol,
                                timeframe=tf,
                                direction=str(raw.get("direction") or "up"),
                                key_price=float(raw.get("nearest_price") or 0),
                                score=float(raw.get("score") or 0),
                                deduper=deduper,
                                sender=send_signal,
                            )
            if tf == "4h":
                mined = mine_hold_correlations(
                    df,
                    origin_mode="wick",
                    daily=frames.get("1d"),
                    weights=orch.settings["confluence"]["weights"],
                    symbol=symbol,
                )
                LearningMemory(orch.store).log_phase("mine", json.dumps({"symbol": symbol, "rules": mined["rules"]}))
                notes.append(f"{symbol} miner hold={mined['n_hold']} fail={mined['n_fail']}")
                if mined["rules"]:
                    write_report(orch, "learn", f"{symbol} hold korelasyonları", "\n".join(mined["rules"]))
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
