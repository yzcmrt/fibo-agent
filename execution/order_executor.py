from __future__ import annotations


class OrderExecutor:
    """Refuses live orders until the user explicitly unlocks Phase 9."""

    def __init__(self, enabled: bool = False, paper_only: bool = True) -> None:
        self.enabled = enabled
        self.paper_only = paper_only

    def place(self, *args, **kwargs) -> None:
        if not self.enabled or self.paper_only:
            raise RuntimeError(
                "Live execution is locked. Complete backtest + paper trading and request explicit approval."
            )
        raise RuntimeError("Live venue wiring is not installed.")
