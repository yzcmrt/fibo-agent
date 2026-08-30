from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ohlcv (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (exchange, symbol, timeframe, ts)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ts ON ohlcv (symbol, timeframe, ts);

CREATE TABLE IF NOT EXISTS funding_oi (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    ts INTEGER NOT NULL,
    funding_rate REAL,
    open_interest REAL,
    PRIMARY KEY (exchange, symbol, ts)
);

CREATE TABLE IF NOT EXISTS dominance (
    asset TEXT NOT NULL,
    ts INTEGER NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (asset, ts)
);

CREATE TABLE IF NOT EXISTS setups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genome_id TEXT,
    exchange TEXT,
    symbol TEXT,
    timeframe TEXT,
    created_ts INTEGER,
    swing_start_ts INTEGER,
    swing_end_ts INTEGER,
    direction TEXT,
    fib_0 REAL,
    fib_1 REAL,
    key_level REAL,
    key_price REAL,
    confluence REAL,
    features_json TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    setup_id INTEGER PRIMARY KEY,
    success INTEGER,
    r_multiple REAL,
    mfe REAL,
    mae REAL,
    bars_to_resolution INTEGER,
    note TEXT
);

CREATE TABLE IF NOT EXISTS genomes (
    id TEXT PRIMARY KEY,
    generation INTEGER,
    params_json TEXT,
    precision REAL,
    recall REAL,
    avg_r REAL,
    n_signals INTEGER,
    fitness REAL,
    created_ts INTEGER
);

CREATE TABLE IF NOT EXISTS correlations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature TEXT,
    success_mean REAL,
    fail_mean REAL,
    weight REAL,
    updated_ts INTEGER
);

CREATE TABLE IF NOT EXISTS phase_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT,
    note TEXT,
    created_ts INTEGER
);

CREATE TABLE IF NOT EXISTS live_drawings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    timeframe TEXT,
    direction TEXT,
    origin_mode TEXT,
    swing_low REAL,
    swing_high REAL,
    levels_json TEXT,
    extensions_json TEXT,
    confluence REAL,
    status TEXT,
    created_ts INTEGER
);

CREATE TABLE IF NOT EXISTS drawing_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drawing_id INTEGER,
    label TEXT,
    note TEXT,
    created_ts INTEGER
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT,
    title TEXT,
    body TEXT,
    created_ts INTEGER
);
"""


class Store:
    def __init__(self, url: str) -> None:
        if url.startswith("sqlite:///"):
            db_path = Path(url.replace("sqlite:///", ""))
            if not db_path.is_absolute():
                root = Path(__file__).resolve().parents[1]
                db_path = root / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{db_path}"
        self.engine = create_engine(
            url,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        with self.engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode=DELETE"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
        self._init_schema()

    def _init_schema(self) -> None:
        raw = self.engine.raw_connection()
        try:
            raw.executescript(SCHEMA_SQL)
            raw.commit()
        finally:
            raw.close()

    def upsert_ohlcv(self, exchange: str, symbol: str, timeframe: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        rows = []
        for ts, row in df.iterrows():
            raw_ts = row["ts"] if "ts" in df.columns else ts
            if hasattr(raw_ts, "timestamp"):
                raw_ts = int(raw_ts.timestamp() * 1000)
            rows.append(
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "ts": int(raw_ts),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
        sql = text(
            """
            INSERT INTO ohlcv (exchange, symbol, timeframe, ts, open, high, low, close, volume)
            VALUES (:exchange, :symbol, :timeframe, :ts, :open, :high, :low, :close, :volume)
            ON CONFLICT(exchange, symbol, timeframe, ts) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume
            """
        )
        with self.engine.begin() as conn:
            conn.execute(sql, rows)
        return len(rows)

    def load_ohlcv(self, exchange: str, symbol: str, timeframe: str) -> pd.DataFrame:
        sql = text(
            """
            SELECT ts, open, high, low, close, volume
            FROM ohlcv
            WHERE exchange=:exchange AND symbol=:symbol AND timeframe=:timeframe
            ORDER BY ts
            """
        )
        with self.engine.begin() as conn:
            df = pd.read_sql(sql, conn, params={"exchange": exchange, "symbol": symbol, "timeframe": timeframe})
        if df.empty:
            return df
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df.set_index("ts")

    def candle_count(self, exchange: str, symbol: str, timeframe: str) -> int:
        sql = text(
            """
            SELECT COUNT(*) AS n FROM ohlcv
            WHERE exchange=:exchange AND symbol=:symbol AND timeframe=:timeframe
            """
        )
        with self.engine.begin() as conn:
            return int(conn.execute(sql, {"exchange": exchange, "symbol": symbol, "timeframe": timeframe}).scalar() or 0)

    def execute(self, sql: str, params: dict[str, Any] | list[dict[str, Any]] | None = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(sql), params or {})

    def query(self, sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self.engine.begin() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
