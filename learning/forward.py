from __future__ import annotations

import json
import time
from typing import Any

import pandas as pd

from analysis.fibonacci import FibGrid, build_fib_from_leg
from analysis.indicators import add_indicators
from analysis.pivots import Pivot
from learning.outcome import label_fib_hold

OPEN_NOTES = {"no_forward_bars", "no_touch"}


def _ts_ms(value: Any) -> int:
    if value is None:
        return 0
    if hasattr(value, "timestamp"):
        return int(value.timestamp() * 1000)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def dump_grid(grid: FibGrid, key_ratio: float) -> str:
    return json.dumps(
        {
            "start_ts": _ts_ms(grid.start.ts),
            "end_ts": _ts_ms(grid.end.ts),
            "start_price": float(grid.start.price),
            "end_price": float(grid.end.price),
            "start_kind": grid.start.kind,
            "end_kind": grid.end.kind,
            "direction": grid.direction,
            "key_ratio": float(key_ratio),
            "origin_mode": getattr(grid, "origin_mode", "wick"),
        }
    )


def _nearest_index(df: pd.DataFrame, ts_ms: int) -> int | None:
    if df.empty or ts_ms <= 0:
        return None
    if "ts" in df.columns:
        stamps = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    else:
        stamps = pd.to_datetime(df.index, utc=True)
    values = pd.Series([int(pd.Timestamp(t).timestamp() * 1000) for t in stamps], dtype="int64")
    loc = int((values - ts_ms).abs().argmin())
    if abs(int(values.iloc[loc]) - ts_ms) > 48 * 3600 * 1000:
        return None
    return loc


def grid_from_payload(df: pd.DataFrame, payload: dict[str, Any]) -> FibGrid | None:
    start_i = _nearest_index(df, int(payload.get("start_ts") or 0))
    end_i = _nearest_index(df, int(payload.get("end_ts") or 0))
    if start_i is None or end_i is None:
        return None
    ts_start = df.index[start_i] if not isinstance(df.index, pd.RangeIndex) else pd.Timestamp(0, tz="UTC")
    ts_end = df.index[end_i] if not isinstance(df.index, pd.RangeIndex) else pd.Timestamp(0, tz="UTC")
    start = Pivot(
        index=start_i,
        ts=pd.Timestamp(ts_start),
        price=float(payload["start_price"]),
        kind=payload.get("start_kind") or "low",
        method="forward",
        threshold=0.0,
    )
    end = Pivot(
        index=end_i,
        ts=pd.Timestamp(ts_end),
        price=float(payload["end_price"]),
        kind=payload.get("end_kind") or "high",
        method="forward",
        threshold=0.0,
    )
    grid = build_fib_from_leg(start, end)
    grid.origin_mode = str(payload.get("origin_mode") or "wick")
    return grid


def enqueue_forward(
    store,
    symbol: str,
    timeframe: str,
    direction: str,
    key_price: float,
    grid: FibGrid | None = None,
    key_ratio: float = 0.618,
) -> None:
    if grid is None:
        return
    store.execute(
        """
        INSERT INTO forward_setups (
            symbol, timeframe, direction, key_price, key_ratio, grid_json,
            created_ts, status
        ) VALUES (
            :symbol, :timeframe, :direction, :key_price, :key_ratio, :grid_json,
            :ts, 'open'
        )
        """,
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "key_price": float(key_price),
            "key_ratio": float(key_ratio),
            "grid_json": dump_grid(grid, key_ratio),
            "ts": int(time.time() * 1000),
        },
    )


def forward_stats(store) -> dict[str, Any]:
    df = store.query("SELECT status, success, r_multiple FROM forward_setups")
    if df.empty:
        return {"n": 0, "open": 0, "done": 0, "precision": None, "avg_r": None}
    done = df[df["status"] == "done"]
    wins = int((done["success"] == 1).sum()) if not done.empty else 0
    avg_r = float(done["r_multiple"].mean()) if not done.empty else None
    return {
        "n": int(len(df)),
        "open": int((df["status"] == "open").sum()),
        "done": int(len(done)),
        "precision": (wins / len(done)) if len(done) else None,
        "avg_r": avg_r,
    }


def resolve_open(
    store,
    symbol: str,
    df: pd.DataFrame,
    horizon_bars: int = 24,
    touch_tolerance_atr: float = 0.25,
    min_continuation_r: float = 1.0,
) -> int:
    open_rows = store.query(
        "SELECT * FROM forward_setups WHERE symbol=:s AND status='open'",
        {"s": symbol},
    )
    if open_rows.empty or df.empty:
        return 0
    work = add_indicators(df) if "atr14" not in df.columns else df
    closed = 0
    for row in open_rows.to_dict(orient="records"):
        raw = row.get("grid_json")
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        grid = grid_from_payload(work, payload)
        if grid is None:
            continue
        key_ratio = float(row.get("key_ratio") or payload.get("key_ratio") or 0.618)
        if key_ratio not in grid.levels:
            # nearest stored key_price wins if ratio missing
            key_ratio = min(grid.levels, key=lambda r: abs(grid.levels[r] - float(row.get("key_price") or 0)))
        out = label_fib_hold(
            work,
            grid,
            key_ratio=key_ratio,
            horizon_bars=horizon_bars,
            touch_tolerance_atr=touch_tolerance_atr,
            min_continuation_r=min_continuation_r,
        )
        if out.note in OPEN_NOTES:
            continue
        store.execute(
            """
            UPDATE forward_setups
            SET status='done', success=:ok, resolve_ts=:ts, r_multiple=:r, note=:note, touched=:touched
            WHERE id=:id
            """,
            {
                "ok": 1 if out.success else 0,
                "ts": int(time.time() * 1000),
                "r": float(out.r_multiple),
                "note": out.note,
                "touched": 1 if out.touched else 0,
                "id": int(row["id"]),
            },
        )
        closed += 1
    return closed
