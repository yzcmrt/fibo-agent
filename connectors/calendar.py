from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from connectors.base import ConnectorResult, now_ms

# Decision / release days only. No rate or CPI forecasts.
FOMC = {
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
}
BOJ = {
    date(2026, 1, 23),
    date(2026, 3, 19),
    date(2026, 4, 28),
    date(2026, 6, 16),
    date(2026, 7, 31),
    date(2026, 9, 18),
    date(2026, 10, 30),
    date(2026, 12, 19),
}
CPI = {
    date(2026, 1, 14),
    date(2026, 2, 12),
    date(2026, 3, 11),
    date(2026, 4, 10),
    date(2026, 5, 13),
    date(2026, 6, 11),
    date(2026, 7, 15),
    date(2026, 8, 12),
    date(2026, 9, 11),
    date(2026, 10, 15),
    date(2026, 11, 13),
    date(2026, 12, 10),
}


def events_on(day: date) -> list[str]:
    names = []
    if day in FOMC:
        names.append("FOMC")
    if day in BOJ:
        names.append("BOJ")
    if day in CPI:
        names.append("CPI")
    return names


def flag_for(day: date, window_days: int = 1) -> dict:
    hits: list[str] = []
    for delta in range(0, window_days + 1):
        hits.extend(events_on(day + timedelta(days=delta)))
    unique = sorted(set(hits))
    return {
        "calendar_flag": 1 if unique else 0,
        "events": unique,
        "date": day.isoformat(),
    }


def fetch(day: date | None = None) -> ConnectorResult:
    today = day or datetime.now(timezone.utc).date()
    payload = flag_for(today)
    return ConnectorResult(
        available=True,
        value=payload,
        source="calendar:static",
        fetched_at=now_ms(),
        error=None,
    )
