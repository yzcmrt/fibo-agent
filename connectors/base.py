from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ConnectorResult:
    available: bool
    value: Any | None
    source: str
    fetched_at: int | None
    error: str | None = None


def now_ms() -> int:
    return int(time.time() * 1000)


def safe_call(source: str, fn: Callable[[], ConnectorResult]) -> ConnectorResult:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return ConnectorResult(
            available=False,
            value=None,
            source=source,
            fetched_at=now_ms(),
            error=f"{type(exc).__name__}: {exc}",
        )
