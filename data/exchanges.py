from __future__ import annotations

import logging
import os
from typing import Any

import ccxt
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ExchangeHub:
    """Public-data clients for OKX (primary) and Bybit (secondary). Binance is not used."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        timeout = settings.get("exchanges", {}).get("timeout_ms", 20000)
        rate_limit = settings.get("exchanges", {}).get("rate_limit", True)
        enabled = settings.get("exchanges", {}).get("enabled", ["okx", "bybit"])
        self.clients: dict[str, ccxt.Exchange] = {}
        self.unavailable: dict[str, str] = {}

        if "okx" in enabled:
            self._init_okx(timeout, rate_limit)
        if "bybit" in enabled:
            self._init_bybit(timeout, rate_limit)
        if not self.clients:
            raise RuntimeError(f"No exchanges available: {self.unavailable}")

    def _init_okx(self, timeout: int, rate_limit: bool) -> None:
        cfg: dict[str, Any] = {
            "enableRateLimit": rate_limit,
            "timeout": timeout,
            "options": {"defaultType": "swap"},
        }
        if os.getenv("OKX_API_KEY"):
            cfg["apiKey"] = os.getenv("OKX_API_KEY")
            cfg["secret"] = os.getenv("OKX_SECRET")
            cfg["password"] = os.getenv("OKX_PASSWORD")
        try:
            client = ccxt.okx(cfg)
            client.load_markets()
            self.clients["okx"] = client
            logger.info("OKX markets loaded: %s", len(client.markets))
        except Exception as exc:  # noqa: BLE001
            self.unavailable["okx"] = str(exc)[:240]
            logger.warning("OKX unavailable: %s", self.unavailable["okx"])

    def _init_bybit(self, timeout: int, rate_limit: bool) -> None:
        cfg: dict[str, Any] = {
            "enableRateLimit": rate_limit,
            "timeout": timeout,
            "options": {
                "defaultType": "swap",
                "fetchMarkets": ["linear"],
            },
        }
        if os.getenv("BYBIT_API_KEY"):
            cfg["apiKey"] = os.getenv("BYBIT_API_KEY")
            cfg["secret"] = os.getenv("BYBIT_SECRET")
        try:
            client = ccxt.bybit(cfg)
            client.load_markets()
            self.clients["bybit"] = client
            logger.info("Bybit linear markets loaded: %s", len(client.markets))
        except Exception as exc:  # noqa: BLE001
            self.unavailable["bybit"] = str(exc)[:240]
            logger.warning("Bybit unavailable: %s", self.unavailable["bybit"])

    def available(self) -> list[str]:
        return list(self.clients.keys())

    def get(self, name: str) -> ccxt.Exchange:
        if name not in self.clients:
            raise RuntimeError(f"Exchange {name} is not available: {self.unavailable.get(name)}")
        return self.clients[name]

    def has_symbol(self, exchange: str, symbol: str) -> bool:
        client = self.clients.get(exchange)
        return bool(client and symbol in client.markets)

    @retry(
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable, ccxt.RateLimitExceeded)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int = 300,
    ) -> list[list[float]]:
        client = self.get(exchange)
        return client.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

    def fetch_funding_rate(self, exchange: str, symbol: str) -> dict[str, Any] | None:
        client = self.get(exchange)
        if not client.has.get("fetchFundingRate"):
            return None
        try:
            return client.fetch_funding_rate(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning("funding rate failed %s %s: %s", exchange, symbol, exc)
            return None

    def fetch_open_interest(self, exchange: str, symbol: str) -> dict[str, Any] | None:
        client = self.get(exchange)
        if not client.has.get("fetchOpenInterest"):
            return None
        try:
            return client.fetch_open_interest(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning("open interest failed %s %s: %s", exchange, symbol, exc)
            return None
