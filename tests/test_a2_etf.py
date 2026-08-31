import importlib.util

from config import ROOT

_spec = importlib.util.spec_from_file_location("etfparse", ROOT / "data" / "etf_parse.py")
etf = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(etf)

SAMPLE = """
<table>
<tr><th>Date</th><th>IBIT</th><th>FBTC</th><th>Total</th></tr>
<tr><td>12 Aug 2026</td><td>100</td><td>20</td><td>120</td></tr>
<tr><td>13 Aug 2026</td><td>(10)</td><td>5</td><td>(5)</td></tr>
<tr><td>Total</td><td>63,365</td><td>10,247</td><td>54,700</td></tr>
</table>
"""


def test_uses_latest_date_total_not_first_fund_or_ytd():
    value, flag = etf.parse_farside_daily_total(SAMPLE)
    assert flag == "etf:farside_daily_total"
    assert value == -5_000_000.0


def test_parse_fail_on_garbage():
    value, flag = etf.parse_farside_daily_total("<html>no table</html>")
    assert value is None
    assert flag == "etf:parse_miss"
