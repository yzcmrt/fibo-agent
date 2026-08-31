from datetime import date

from connectors.calendar import fetch, flag_for


def test_fomc_day_flagged():
    payload = flag_for(date(2026, 9, 16), window_days=0)
    assert payload["calendar_flag"] == 1
    assert "FOMC" in payload["events"]


def test_quiet_day_zero():
    payload = flag_for(date(2026, 8, 31), window_days=0)
    assert payload["calendar_flag"] == 0
    assert payload["events"] == []


def test_fetch_connector():
    out = fetch(date(2026, 8, 12))
    assert out.available is True
    assert out.value["calendar_flag"] == 1
    assert "CPI" in out.value["events"]
