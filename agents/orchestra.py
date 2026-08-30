from __future__ import annotations

import logging
from typing import Any

from analysis.fibonacci import grids_from_pivots
from analysis.indicators import add_indicators, snapshot_features
from analysis.macro_regime import classify_regime
from analysis.pivots import detect_pivots
from analysis.support_resistance import cluster_sr
from analysis.trendlines import detect_trendlines
from analysis.volume_profile import volume_profile
from data.dominance import DominanceClient
from data.exchanges import ExchangeHub
from data.fetch import HistoryIngestor
from data.store import Store
from learning.correlator import FeatureCorrelator
from learning.memory import LearningMemory
from learning.trainer import EvolutionaryTrainer, default_genome
from signals.confluence import score_setup
from signals.llm_interpreter import interpret_setup

logger = logging.getLogger(__name__)


class AgentOrchestra:
    """Coordinator for the specialist agents.

    Agents:
      data       — ingest and sanity-check market data
      geometry   — pivots, fibonacci, trendlines, S/R
      indicator  — RSI/EMA/volume features + learned model
      regime     — dominance snapshot
      teacher    — evolutionary search over fib-drawing genomes
      confluence — weighted setup score
    """

    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self.store = Store(settings["database"]["url"])
        self.hub = ExchangeHub(settings)
        self.ingest = HistoryIngestor(self.hub, self.store, settings)
        self.dominance = DominanceClient(self.store)
        self.memory = LearningMemory(self.store)
        self.correlator = FeatureCorrelator()
        saved = self.memory.load_correlations()
        if saved:
            weights, means = saved
            self.correlator.load_state(weights, means)
        self.trainer = EvolutionaryTrainer(settings, self.memory, self.correlator)

    def ingest_symbol(self, exchange: str, symbol: str, timeframe: str, min_candles: int):
        df = self.ingest.backfill(exchange, symbol, timeframe, min_candles)
        logger.info("ingested %s %s %s rows=%s", exchange, symbol, timeframe, len(df))
        return df

    def analyze(self, df, params: dict[str, Any] | None = None, regime: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or default_genome(self.settings)
        work = add_indicators(df)
        pivots = detect_pivots(work, method=params["method"], threshold=float(params["threshold"]))
        grids = grids_from_pivots(pivots, last_n_legs=6)
        zones = cluster_sr(pivots, cluster_pct=self.settings["support_resistance"]["cluster_pct"])
        lines = detect_trendlines(pivots)
        profile = volume_profile(work, lookback=self.settings["volume"]["lookback"])
        regime = regime or classify_regime(None, None)
        last_i = len(work) - 1
        price = float(work["close"].iloc[-1])
        atr = float(work["atr14"].iloc[-1] or price * 0.01)
        scored = []
        for grid in grids[-3:]:
            raw = score_setup(
                price=price,
                grid=grid,
                zones=zones,
                lines=lines,
                profile=profile,
                regime=regime,
                model_prob=None,
                atr=atr,
                weights=self.settings["confluence"]["weights"],
                bar_index=last_i,
            )
            feats = snapshot_features(work, last_i)
            feats["atr_pct"] = atr / max(price, 1e-9)
            feats["fib_ratio"] = raw["nearest_ratio"]
            feats["confluence"] = raw["score"]
            raw["model_prob"] = self.correlator.predict_proba(feats)
            raw["narrative"] = interpret_setup(
                {
                    "direction": raw["direction"],
                    "nearest_ratio": raw["nearest_ratio"],
                    "score": raw["score"],
                    "regime_label": regime.get("label"),
                    "parts": raw["parts"],
                }
            )
            scored.append({"grid": grid, "score": raw})
        return {
            "pivots": pivots,
            "grids": grids,
            "zones": zones,
            "lines": lines,
            "profile": profile,
            "regime": regime,
            "scored": scored,
            "params": params,
        }

    def train(self, df) -> dict[str, Any]:
        result = self.trainer.run(df)
        self.memory.log_phase("train", f"best={result['best']}")
        return result
