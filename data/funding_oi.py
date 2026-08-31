from __future__ import annotations

import logging
import time
from typing import Any

from analysis.oi_rules import encode_oi_rule, funding_roc, label_oi_price

logger = logging.getLogger(__name__)


def persist_snapshot(hub, store, exchange: str, symbol: str) -> dict[str, Any]:
    ts = int(time.time() * 1000)
    fr = hub.fetch_funding_rate(exchange, symbol) or {}
    oi = hub.fetch_open_interest(exchange, symbol) or {}
    rate = fr.get("fundingRate", fr.get("funding_rate"))
    interest = oi.get("openInterestAmount", oi.get("openInterest", oi.get("open_interest")))
    try:
        rate_f = float(rate) if rate is not None else None
    except (TypeError, ValueError):
        rate_f = None
    try:
        oi_f = float(interest) if interest is not None else None
    except (TypeError, ValueError):
        oi_f = None
    store.upsert_funding_oi(
        {
            "exchange": exchange,
            "symbol": symbol,
            "ts": ts,
            "funding_rate": rate_f,
            "open_interest": oi_f,
        }
    )
    return {"funding_rate": rate_f, "open_interest": oi_f, "ts": ts}


def latest_features(store, exchange: str, symbol: str, price_ret: float = 0.0) -> dict[str, float]:
    df = store.load_funding_oi(exchange, symbol)
    if df is None or df.empty:
        return {"oi_rule": 0.0, "funding_roc": 0.0, "oi_available": 0.0}
    oi_now = df["open_interest"].iloc[-1]
    oi_prev = df["open_interest"].iloc[-2] if len(df) > 1 else oi_now
    fr_now = df["funding_rate"].iloc[-1]
    fr_prev = df["funding_rate"].iloc[-2] if len(df) > 1 else fr_now
    oi_ret = 0.0
    try:
        if oi_now == oi_now and oi_prev == oi_prev and float(oi_prev) != 0:
            oi_ret = (float(oi_now) - float(oi_prev)) / abs(float(oi_prev))
    except (TypeError, ValueError):
        oi_ret = 0.0
    label = label_oi_price(price_ret, oi_ret)
    return {
        "oi_rule": encode_oi_rule(label),
        "funding_roc": funding_roc(
            None if fr_now != fr_now else float(fr_now),
            None if fr_prev != fr_prev else float(fr_prev),
        ),
        "oi_available": 1.0 if oi_now == oi_now else 0.0,
    }
