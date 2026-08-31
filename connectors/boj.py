from __future__ import annotations

from connectors.base import ConnectorResult, now_ms, safe_call


def fetch() -> ConnectorResult:
    def _run() -> ConnectorResult:
        from data.macro import fetch_fred_last, fetch_usdjpy

        jgb = fetch_fred_last("IRLTLT01JPM156N")
        usdjpy, flag = fetch_usdjpy()
        ok = jgb is not None or usdjpy is not None
        return ConnectorResult(
            available=ok,
            value={"jgb_10y": jgb, "usdjpy": usdjpy},
            source=f"jgb:{'fred' if jgb is not None else 'unavailable'}|{flag}",
            fetched_at=now_ms(),
            error=None if ok else "boj:unavailable",
        )

    return safe_call("boj", _run)
