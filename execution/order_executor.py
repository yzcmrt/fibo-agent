from __future__ import annotations

import time
from typing import Any

from execution.kill_switch import is_killed
from execution.risk_manager import RiskManager


class OrderExecutor:
    """Paper/demo by default. Live venue wiring stays locked."""

    def __init__(self, store, settings: dict[str, Any], risk: RiskManager | None = None) -> None:
        exe = settings.get("execution", {})
        self.store = store
        self.enabled = bool(exe.get("enabled", False))
        self.paper_only = bool(exe.get("paper_only", True))
        self.demo = bool(exe.get("demo", True))
        self.venue = str(exe.get("venue", "okx"))
        self.risk = risk or RiskManager(
            risk_pct=float(exe.get("risk_pct", 0.005)),
            max_daily_r=float(exe.get("max_daily_r", -3.0)),
            max_positions=int(exe.get("max_positions", 3)),
            max_symbol_notional=float(exe.get("max_symbol_notional", 250.0)),
        )

    def place(self, symbol: str, side: str, qty: float, price: float, note: str = "") -> dict[str, Any]:
        if is_killed(self.store) or not self.enabled:
            return self._paper(symbol, side, qty, price, "blocked:" + (note or "kill_or_disabled"))
        notional = abs(qty * price)
        if not self.risk.allow(symbol, notional):
            return self._paper(symbol, side, qty, price, "risk_block")
        if self.paper_only or self.demo:
            fill = self._paper(symbol, side, qty, price, note or "paper_or_demo")
            self.risk.on_fill(symbol, notional)
            return fill
        raise RuntimeError("Live venue wiring is locked until staged autonomy gates pass.")

    def _paper(self, symbol: str, side: str, qty: float, price: float, note: str) -> dict[str, Any]:
        row = {
            "venue": self.venue,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "paper",
            "note": note,
            "created_ts": int(time.time() * 1000),
        }
        self.store.execute(
            """
            INSERT INTO paper_fills (venue, symbol, side, qty, price, status, note, created_ts)
            VALUES (:venue, :symbol, :side, :qty, :price, :status, :note, :created_ts)
            """,
            row,
        )
        return row
