from __future__ import annotations

import re

_MONTHS = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
)
_DATE_ROW = re.compile(
    r"^\s*(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(20\d{2})\b",
    re.I,
)


def parse_flow_cell(text: str) -> float | None:
    raw = text.strip().replace(",", "").replace("$", "").replace("\xa0", "")
    if not raw or raw in {".", "-", "–"}:
        return None
    neg = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()%")
    try:
        value = float(raw)
    except ValueError:
        return None
    return -value if neg else value


def parse_farside_daily_total(html: str) -> tuple[float | None, str]:
    """Latest dated row, last numeric cell. Ignores footer Total (YTD)."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    dated: list[list[str]] = []
    for row in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, flags=re.I | re.S)
        texts = [re.sub(r"<[^>]+>", " ", c).strip() for c in cells]
        texts = [re.sub(r"\s+", " ", t) for t in texts if t]
        if texts and _DATE_ROW.match(texts[0]):
            dated.append(texts)
    if not dated:
        return None, "etf:parse_miss"
    last = dated[-1]
    for cell in reversed(last[1:]):
        parsed = parse_flow_cell(cell)
        if parsed is not None:
            return parsed * 1_000_000.0, "etf:farside_daily_total"
    return None, "etf:parse_miss"
