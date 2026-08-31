from __future__ import annotations

import time
from typing import Any


def signal_key(
    symbol: str,
    timeframe: str,
    direction: str,
    key_price: float,
    score: float,
) -> str:
    band = int(float(score) // 5) * 5
    price = round(float(key_price), 4)
    return f"{symbol}|{timeframe}|{direction}|{price}|{band}"


class SignalDeduper:
    def __init__(self, cooldown_s: int = 8 * 3600, store=None) -> None:
        self.cooldown_s = cooldown_s
        self.store = store
        self._mem: dict[str, int] = {}

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _load(self, key: str) -> int | None:
        if key in self._mem:
            return self._mem[key]
        if self.store is None:
            return None
        name = f"alert:{key}"
        df = self.store.query("SELECT value FROM runtime_flags WHERE name=:n", {"n": name})
        if df.empty:
            return None
        try:
            return int(df.iloc[0]["value"])
        except (TypeError, ValueError):
            return None

    def _save(self, key: str, ts_ms: int) -> None:
        self._mem[key] = ts_ms
        if self.store is None:
            return
        self.store.execute(
            """
            INSERT INTO runtime_flags (name, value, updated_ts)
            VALUES (:n, :v, :t)
            ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts
            """,
            {"n": f"alert:{key}", "v": str(ts_ms), "t": ts_ms},
        )

    def allow(self, key: str, now_ms: int | None = None) -> bool:
        now = now_ms if now_ms is not None else self._now_ms()
        last = self._load(key)
        if last is not None and now - last < self.cooldown_s * 1000:
            return False
        self._save(key, now)
        return True


def notify_setup(
    *,
    text: str,
    symbol: str,
    timeframe: str,
    direction: str,
    key_price: float,
    score: float,
    deduper: SignalDeduper,
    sender,
) -> bool:
    key = signal_key(symbol, timeframe, direction, key_price, score)
    if not deduper.allow(key):
        return False
    return bool(sender(text))
