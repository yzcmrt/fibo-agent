from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import requests

from data.store import Store

logger = logging.getLogger(__name__)


class DominanceClient:
    """USDT.D / USDC.D / BTC.D snapshots via CoinGecko global endpoint."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.session = requests.Session()

    def fetch_snapshot(self) -> dict[str, float]:
        url = "https://api.coingecko.com/api/v3/global"
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        payload = resp.json()["data"]["market_cap_percentage"]
        mapping = {
            "BTC.D": float(payload.get("btc") or 0.0),
            "ETH.D": float(payload.get("eth") or 0.0),
            "USDT.D": float(payload.get("usdt") or 0.0),
            "USDC.D": float(payload.get("usdc") or 0.0),
        }
        ts = int(time.time() * 1000)
        rows = [{"asset": k, "ts": ts, "value": v} for k, v in mapping.items() if v]
        if rows:
            sql = """
            INSERT INTO dominance (asset, ts, value)
            VALUES (:asset, :ts, :value)
            ON CONFLICT(asset, ts) DO UPDATE SET value=excluded.value
            """
            self.store.execute(sql, rows)
        return mapping

    def load_series(self, asset: str) -> pd.DataFrame:
        df = self.store.query(
            "SELECT ts, value FROM dominance WHERE asset=:a ORDER BY ts",
            {"a": asset},
        )
        if df.empty:
            return df
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df.set_index("ts")

    def regime_label(self, snapshot: dict[str, float] | None = None) -> dict[str, Any]:
        snap = snapshot or self.fetch_snapshot()
        usdt = snap.get("USDT.D", 0.0)
        btc = snap.get("BTC.D", 0.0)
        # Rising stablecoin dominance = risk-off for alts. Snapshot-only until history exists.
        if usdt >= 6.5:
            label = "risk_off"
        elif usdt <= 4.5:
            label = "risk_on"
        else:
            label = "neutral"
        return {"label": label, "usdt_d": usdt, "btc_d": btc, "usdc_d": snap.get("USDC.D", 0.0)}
