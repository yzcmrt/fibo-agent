from __future__ import annotations


class RiskManager:
    def __init__(self, risk_pct: float = 0.005, max_daily_r: float = -3.0) -> None:
        self.risk_pct = risk_pct
        self.max_daily_r = max_daily_r
        self.realized_r_today = 0.0

    def allow(self) -> bool:
        return self.realized_r_today > self.max_daily_r

    def size(self, equity: float, entry: float, stop: float) -> float:
        risk = abs(entry - stop)
        if risk <= 0:
            return 0.0
        return (equity * self.risk_pct) / risk
