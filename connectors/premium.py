from __future__ import annotations

from connectors.base import ConnectorResult, now_ms, safe_call


def fetch() -> ConnectorResult:
    def _run() -> ConnectorResult:
        from data.macro import fetch_coinbase_premium

        value, flag = fetch_coinbase_premium()
        ok = value is not None
        return ConnectorResult(ok, value, flag, now_ms(), None if ok else flag)

    return safe_call("premium", _run)
