from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd

from data.exchanges import ExchangeHub
from data.sanity import sanity_check
from data.store import Store

logger = logging.getLogger(__name__)


def ohlcv_to_df(raw: list[list[float]]) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset=["ts"]).sort_values("ts")
    df["ts"] = df["ts"].astype("int64")
    return df.set_index(pd.to_datetime(df["ts"], unit="ms", utc=True))


class HistoryIngestor:
    def __init__(self, hub: ExchangeHub, store: Store, settings: dict[str, Any]) -> None:
        self.hub = hub
        self.store = store
        self.settings = settings

    def backfill(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        min_candles: int,
    ) -> pd.DataFrame:
        existing = self.store.candle_count(exchange, symbol, timeframe)
        logger.info("existing candles %s %s %s = %s", exchange, symbol, timeframe, existing)
        since = None
        if existing:
            last = self.store.query(
                """
                SELECT MAX(ts) AS ts FROM ohlcv
                WHERE exchange=:e AND symbol=:s AND timeframe=:tf
                """,
                {"e": exchange, "s": symbol, "tf": timeframe},
            )
            if not last.empty and last.iloc[0]["ts"] is not None:
                since = int(last.iloc[0]["ts"]) + 1

        fetched = 0
        safety = 0
        limit = int(self.settings["history"]["fetch_limit"])
        while existing + fetched < min_candles and safety < 80:
            safety += 1
            if since is None:
                # walk backward from now
                lookback_ms = self._tf_ms(timeframe) * min_candles
                since = int(time.time() * 1000) - lookback_ms
            batch = self.hub.fetch_ohlcv(exchange, symbol, timeframe, since=since, limit=limit)
            if not batch:
                break
            df = ohlcv_to_df(batch)
            written = self.store.upsert_ohlcv(exchange, symbol, timeframe, df)
            fetched += written
            last_ts = int(df["ts"].iloc[-1])
            if last_ts <= since:
                break
            since = last_ts + 1
            if len(batch) < max(10, limit // 4):
                break
            time.sleep(0.15)

        full = self.store.load_ohlcv(exchange, symbol, timeframe)
        report = sanity_check(full)
        logger.info("sanity %s %s %s: %s", exchange, symbol, timeframe, report)
        return full

    @staticmethod
    def _tf_ms(timeframe: str) -> int:
        unit = timeframe[-1]
        n = int(timeframe[:-1])
        mult = {"m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000}[unit]
        return n * mult
