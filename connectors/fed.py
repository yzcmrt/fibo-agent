from __future__ import annotations

from connectors.base import ConnectorResult, now_ms, safe_call


def fetch() -> ConnectorResult:
    def _run() -> ConnectorResult:
        from data.fed import fetch_fed_probs

        hold, cut, flag = fetch_fed_probs()
        ok = hold is not None or cut is not None
        return ConnectorResult(
            available=ok,
            value={"hold": hold, "cut": cut},
            source=flag,
            fetched_at=now_ms(),
            error=None if ok else flag,
        )

    return safe_call("fed", _run)
