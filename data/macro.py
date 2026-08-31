from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import pandas as pd
import requests

from analysis.macro_regime import classify_regime
from data.store import Store

logger = logging.getLogger(__name__)


def _get(url: str, timeout: int = 20) -> requests.Response | None:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "fibo-agent/0.2"})
        resp.raise_for_status()
        return resp
    except Exception as exc:  # noqa: BLE001
        logger.warning("macro GET failed %s: %s", url, exc)
        return None


def fetch_etf_flow() -> tuple[float | None, str]:
    from data.etf_parse import parse_farside_daily_total

    resp = _get("https://farside.co.uk/btc/")
    if resp is None:
        return None, "etf:unavailable"
    return parse_farside_daily_total(resp.text)


def fetch_coinbase_premium() -> tuple[float | None, str]:
    cb = _get("https://api.exchange.coinbase.com/products/BTC-USD/ticker")
    okx = _get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT")
    if cb is None or okx is None:
        return None, "premium:unavailable"
    try:
        cb_px = float(cb.json()["price"])
        okx_px = float(okx.json()["data"][0]["last"])
        if okx_px <= 0:
            return None, "premium:bad_px"
        return (cb_px - okx_px) / okx_px * 100.0, "premium:cb-okx"
    except Exception as exc:  # noqa: BLE001
        logger.warning("premium parse: %s", exc)
        return None, "premium:parse_miss"


def fetch_fred_last(series_id: str) -> float | None:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    resp = _get(url)
    if resp is None:
        return None
    try:
        lines = [ln for ln in resp.text.splitlines() if ln and not ln.startswith("DATE")]
        for line in reversed(lines):
            parts = line.split(",")
            if len(parts) < 2 or parts[1] in {".", ""}:
                continue
            return float(parts[1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("fred parse %s: %s", series_id, exc)
    return None


def fetch_usdjpy() -> tuple[float | None, str]:
    resp = _get("https://api.exchangerate.host/latest?base=USD&symbols=JPY")
    if resp is None:
        return None, "usdjpy:unavailable"
    try:
        return float(resp.json()["rates"]["JPY"]), "usdjpy:exchangerate"
    except Exception:
        return None, "usdjpy:parse_miss"


def last_known(store: Store) -> dict[str, Any]:
    df = store.query("SELECT * FROM macro_snapshot ORDER BY ts DESC LIMIT 1")
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def collect_snapshot(store: Store, dominance: dict[str, float] | None = None) -> dict[str, Any]:
    from connectors import boj as boj_c
    from connectors import calendar as cal_c
    from connectors import etf as etf_c
    from connectors import fed as fed_c
    from connectors import premium as prem_c

    prev = last_known(store)
    flags: list[str] = []
    etf_r = etf_c.fetch()
    flags.append(etf_r.source if etf_r.available else (etf_r.error or etf_r.source))
    prem_r = prem_c.fetch()
    flags.append(prem_r.source if prem_r.available else (prem_r.error or prem_r.source))
    boj_r = boj_c.fetch()
    flags.append(boj_r.source)
    fed_r = fed_c.fetch()
    flags.append(fed_r.source if fed_r.available else (fed_r.error or fed_r.source))
    cal_r = cal_c.fetch()
    if cal_r.available and isinstance(cal_r.value, dict):
        ev = list(cal_r.value.get("events") or [])
        flags.append("calendar:" + (",".join(ev) if ev else "quiet"))
    else:
        flags.append(cal_r.error or cal_r.source)
    etf = etf_r.value if etf_r.available else None
    prem = prem_r.value if prem_r.available else None
    boj_val = boj_r.value or {}
    jgb = boj_val.get("jgb_10y")
    usdjpy = boj_val.get("usdjpy")
    fed_val = fed_r.value or {}
    fed_hold = fed_val.get("hold") if fed_r.available else None
    fed_cut = fed_val.get("cut") if fed_r.available else None

    row = {
        "ts": int(time.time() * 1000),
        "etf_net_flow_usd": etf,
        "coinbase_premium_pct": prem if prem is not None else prev.get("coinbase_premium_pct"),
        "fed_hold_prob": fed_hold,
        "fed_cut_prob": fed_cut,
        "jgb_10y": jgb if jgb is not None else prev.get("jgb_10y"),
        "usdjpy": usdjpy if usdjpy is not None else prev.get("usdjpy"),
        "usdt_d": (dominance or {}).get("USDT.D", prev.get("usdt_d")),
        "btc_d": (dominance or {}).get("BTC.D", prev.get("btc_d")),
        "source_flags": json.dumps(flags),
    }
    store.execute(
        """
        INSERT INTO macro_snapshot (
            ts, etf_net_flow_usd, coinbase_premium_pct, fed_hold_prob, fed_cut_prob,
            jgb_10y, usdjpy, usdt_d, btc_d, source_flags
        ) VALUES (
            :ts, :etf_net_flow_usd, :coinbase_premium_pct, :fed_hold_prob, :fed_cut_prob,
            :jgb_10y, :usdjpy, :usdt_d, :btc_d, :source_flags
        )
        ON CONFLICT(ts) DO UPDATE SET
            etf_net_flow_usd=excluded.etf_net_flow_usd,
            coinbase_premium_pct=excluded.coinbase_premium_pct,
            jgb_10y=excluded.jgb_10y,
            usdjpy=excluded.usdjpy,
            usdt_d=excluded.usdt_d,
            btc_d=excluded.btc_d,
            source_flags=excluded.source_flags
        """,
        row,
    )
    return row


def regime_from_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    base = classify_regime(row.get("usdt_d"), row.get("btc_d"))
    premium = float(row.get("coinbase_premium_pct") or 0.0) if row.get("coinbase_premium_pct") is not None else 0.0
    flow_raw = row.get("etf_net_flow_usd")
    flow = float(flow_raw) if flow_raw is not None else None
    if flow is not None and premium > 0.15 and flow > 0:
        base["alt_bias"] = min(1.0, float(base["alt_bias"]) + 0.25)
        base["label"] = "risk_on" if base["label"] != "risk_off" else base["label"]
    if flow is not None and premium < -0.15 and flow < 0:
        base["alt_bias"] = max(-1.0, float(base["alt_bias"]) - 0.25)
        base["label"] = "risk_off" if base["label"] != "risk_on" else base["label"]
    base["macro"] = {
        "premium": premium,
        "etf_flow": flow,
        "jgb_10y": row.get("jgb_10y"),
        "usdjpy": row.get("usdjpy"),
        "flags": row.get("source_flags"),
    }
    return base
