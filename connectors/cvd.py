from __future__ import annotations

from connectors.base import ConnectorResult, now_ms, safe_call


def status(store, exchange: str, symbol: str, market: str = "swap", timeframe: str = "4h") -> ConnectorResult:
    def _run() -> ConnectorResult:
        df = store.load_cvd(exchange, symbol, market, timeframe)
        if df is None or getattr(df, "empty", True):
            return ConnectorResult(False, None, "cvd", now_ms(), "cvd:no_rows")
        last = df.iloc[-1].to_dict()
        return ConnectorResult(True, last, "cvd", now_ms(), None)

    return safe_call("cvd", _run)
