from __future__ import annotations

from connectors.base import ConnectorResult, now_ms, safe_call


def fetch() -> ConnectorResult:
    def _run() -> ConnectorResult:
        from data.macro import fetch_etf_flow

        value, flag = fetch_etf_flow()
        ok = value is not None and flag.startswith("etf:farside")
        return ConnectorResult(
            available=ok,
            value=value,
            source=flag,
            fetched_at=now_ms(),
            error=None if ok else flag,
        )

    return safe_call("etf", _run)
