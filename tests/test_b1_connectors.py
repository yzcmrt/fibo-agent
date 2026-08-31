from connectors.base import ConnectorResult, safe_call
from connectors.calendar import fetch as fetch_calendar


def test_safe_call_swallows_exception():
    def boom() -> ConnectorResult:
        raise RuntimeError("forced")

    out = safe_call("etf", boom)
    assert out.available is False
    assert out.value is None
    assert out.source == "etf"
    assert "forced" in (out.error or "")


def test_calendar_static_available():
    out = fetch_calendar()
    assert out.available is True
    assert out.value is not None
    assert "calendar_flag" in out.value
