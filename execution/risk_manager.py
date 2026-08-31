from __future__ import annotations

from datetime import datetime, timezone


class RiskManager:
    def __init__(
        self,
        risk_pct: float = 0.005,
        max_daily_r: float = -3.0,
        max_positions: int = 3,
        max_symbol_notional: float = 250.0,
    ) -> None:
        self.risk_pct = risk_pct
        self.max_daily_r = max_daily_r
        self.max_positions = max_positions
        self.max_symbol_notional = max_symbol_notional
        self.realized_r_today = 0.0
        self.open_positions = 0
        self.notional_by_symbol: dict[str, float] = {}
        self._day = datetime.now(timezone.utc).date()

    def _roll_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            self._day = today
            self.realized_r_today = 0.0

    def allow(self, symbol: str | None = None, notional: float = 0.0) -> bool:
        self._roll_day()
        if self.realized_r_today <= self.max_daily_r:
            return False
        if self.open_positions >= self.max_positions:
            return False
        if symbol:
            current = self.notional_by_symbol.get(symbol, 0.0)
            if current + notional > self.max_symbol_notional:
                return False
        return True

    def size(self, equity: float, entry: float, stop: float) -> float:
        risk = abs(entry - stop)
        if risk <= 0:
            return 0.0
        return (equity * self.risk_pct) / risk

    def on_fill(self, symbol: str, notional: float) -> None:
        self.open_positions += 1
        self.notional_by_symbol[symbol] = self.notional_by_symbol.get(symbol, 0.0) + notional

    def on_close(self, symbol: str, realized_r: float, notional: float) -> None:
        self._roll_day()
        self.realized_r_today += realized_r
        self.open_positions = max(0, self.open_positions - 1)
        self.notional_by_symbol[symbol] = max(0.0, self.notional_by_symbol.get(symbol, 0.0) - notional)
