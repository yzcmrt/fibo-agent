from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def classify_side(trade: dict[str, Any], prev_price: float | None) -> str:
    side = str(trade.get("side") or "").lower()
    if side in {"buy", "sell"}:
        return side
    price = float(trade.get("price") or 0.0)
    if prev_price is None or price == prev_price:
        return "buy"
    return "buy" if price > prev_price else "sell"


def aggregate_trades(trades: list[dict[str, Any]], timeframe: str) -> list[dict[str, float]]:
    width = TF_MS[timeframe]
    buckets: dict[int, dict[str, float]] = {}
    prev = None
    for trade in sorted(trades, key=lambda t: int(t.get("timestamp") or 0)):
        ts = int(trade.get("timestamp") or 0)
        if ts <= 0:
            continue
        bar_ts = ts - (ts % width)
        bucket = buckets.setdefault(bar_ts, {"buy_vol": 0.0, "sell_vol": 0.0})
        amount = float(trade.get("amount") or 0.0)
        side = classify_side(trade, prev)
        if side == "buy":
            bucket["buy_vol"] += amount
        else:
            bucket["sell_vol"] += amount
        prev = float(trade.get("price") or prev or 0.0)
    rows = []
    cum = 0.0
    for ts in sorted(buckets):
        buy = buckets[ts]["buy_vol"]
        sell = buckets[ts]["sell_vol"]
        delta = buy - sell
        cum += delta
        rows.append(
            {
                "ts": ts,
                "buy_vol": buy,
                "sell_vol": sell,
                "delta": delta,
                "cumulative_delta": cum,
            }
        )
    return rows


def rebase_cumulative(rows: list[dict[str, float]], last_cum: float = 0.0) -> list[dict[str, float]]:
    if not rows:
        return []
    first = rows[0]["cumulative_delta"]
    shift = last_cum - first + rows[0]["delta"]
    out = []
    running = last_cum
    for row in rows:
        running += row["delta"]
        item = dict(row)
        item["cumulative_delta"] = running
        out.append(item)
    return out


def cvd_slope(values: list[float], lookback: int = 6) -> float:
    if len(values) < 2:
        return 0.0
    window = values[-lookback:]
    return (window[-1] - window[0]) / max(abs(window[0]), 1.0)


def cvd_divergence(price_highs: list[float], cvd_vals: list[float]) -> float:
    """+1 bearish div (price HH, cvd not), -1 bullish div, 0 none."""
    if len(price_highs) < 4 or len(cvd_vals) < 4:
        return 0.0
    p1, p2 = price_highs[-3], price_highs[-1]
    c1, c2 = cvd_vals[-3], cvd_vals[-1]
    if p2 > p1 and c2 < c1:
        return 1.0
    if p2 < p1 and c2 > c1:
        return -1.0
    return 0.0


def _bar_ts_ms(frame: pd.DataFrame) -> pd.Series:
    if "ts" in frame.columns:
        raw = frame["ts"]
        if pd.api.types.is_datetime64_any_dtype(raw):
            return pd.Series([int(pd.Timestamp(t).timestamp() * 1000) for t in raw], index=frame.index)
        return pd.to_numeric(raw, errors="coerce").astype("int64")
    return pd.Series([int(pd.Timestamp(t).timestamp() * 1000) for t in pd.to_datetime(frame.index, utc=True)], index=frame.index)


def attach_cvd_features(ohlcv: pd.DataFrame, cvd: pd.DataFrame) -> pd.DataFrame:
    out = ohlcv.copy()
    out["cvd_slope"] = 0.0
    out["cvd_div"] = 0.0
    out["cvd_cum"] = 0.0
    out["cvd_available"] = 0.0
    if cvd is None or cvd.empty or "cumulative_delta" not in cvd.columns:
        return out
    left = pd.DataFrame({"ts": _bar_ts_ms(out), "high": out["high"].to_numpy()})
    right = pd.DataFrame(
        {
            "ts": pd.to_numeric(cvd["ts"], errors="coerce").astype("int64"),
            "cumulative_delta": pd.to_numeric(cvd["cumulative_delta"], errors="coerce"),
        }
    ).dropna().sort_values("ts")
    left = left.sort_values("ts")
    merged = pd.merge_asof(left, right, on="ts", direction="backward")
    merged = merged.sort_index()
    cum = merged["cumulative_delta"]
    prev = cum.shift(6)
    slope = (cum - prev) / prev.abs().clip(lower=1.0)
    px = merged["high"]
    div = pd.Series(0.0, index=merged.index)
    div[(px > px.shift(3)) & (cum < cum.shift(3))] = 1.0
    div[(px < px.shift(3)) & (cum > cum.shift(3))] = -1.0
    out["cvd_cum"] = cum.fillna(0.0).to_numpy()
    out["cvd_slope"] = slope.fillna(0.0).to_numpy()
    out["cvd_div"] = div.fillna(0.0).to_numpy()
    out["cvd_available"] = cum.notna().astype(float).to_numpy()
    return out


class CvdCollector:
    """REST poll first. watch_trades if ccxt pro exists. Never crash the worker."""

    def __init__(self, hub, store) -> None:
        self.hub = hub
        self.store = store

    def fetch_recent(
        self,
        exchange: str,
        symbol: str,
        limit: int = 500,
        since: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            client = self.hub.get(exchange)
            if since:
                return client.fetch_trades(symbol, since=since, limit=limit) or []
            return client.fetch_trades(symbol, limit=limit) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("cvd fetch_trades failed %s %s: %s", exchange, symbol, exc)
            return []

    def ingest_bar(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        market: str = "swap",
    ) -> int:
        existing = self.store.load_cvd(exchange, symbol, market, timeframe)
        last_ts = int(existing["ts"].iloc[-1]) if not existing.empty else 0
        trades = self.fetch_recent(exchange, symbol, since=last_ts or None)
        rows = aggregate_trades(trades, timeframe)
        if not rows:
            return 0
        last_delta = float(existing["delta"].iloc[-1]) if not existing.empty else 0.0
        last_cum = float(existing["cumulative_delta"].iloc[-1]) if not existing.empty else 0.0
        prev_cum = last_cum - last_delta if not existing.empty else 0.0
        payload = []
        running = prev_cum if last_ts and any(int(r["ts"]) == last_ts for r in rows) else last_cum
        for row in rows:
            ts = int(row["ts"])
            if ts < last_ts:
                continue
            if ts == last_ts:
                running = prev_cum + row["delta"]
            else:
                running += row["delta"]
            payload.append(
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "market": market,
                    "timeframe": timeframe,
                    "ts": ts,
                    "buy_vol": row["buy_vol"],
                    "sell_vol": row["sell_vol"],
                    "delta": row["delta"],
                    "cumulative_delta": running,
                }
            )
        return self.store.upsert_cvd(payload)
