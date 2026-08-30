from __future__ import annotations

import json
import time
from typing import Any

from data.store import Store


class LearningMemory:
    def __init__(self, store: Store) -> None:
        self.store = store

    def save_genome(self, genome_id: str, generation: int, params: dict[str, Any], metrics: dict[str, float]) -> None:
        self.store.execute(
            """
            INSERT INTO genomes (id, generation, params_json, precision, recall, avg_r, n_signals, fitness, created_ts)
            VALUES (:id, :generation, :params_json, :precision, :recall, :avg_r, :n_signals, :fitness, :created_ts)
            ON CONFLICT(id) DO UPDATE SET
                precision=excluded.precision, recall=excluded.recall, avg_r=excluded.avg_r,
                n_signals=excluded.n_signals, fitness=excluded.fitness
            """,
            {
                "id": genome_id,
                "generation": generation,
                "params_json": json.dumps(params),
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "avg_r": metrics.get("avg_r", 0.0),
                "n_signals": int(metrics.get("n_signals", 0)),
                "fitness": metrics.get("fitness", 0.0),
                "created_ts": int(time.time() * 1000),
            },
        )

    def best_genome(self) -> dict[str, Any] | None:
        df = self.store.query("SELECT * FROM genomes ORDER BY fitness DESC LIMIT 1")
        if df.empty:
            return None
        row = df.iloc[0].to_dict()
        row["params"] = json.loads(row["params_json"])
        return row

    def save_correlations(self, weights: dict[str, float], means: dict[str, tuple[float, float]]) -> None:
        ts = int(time.time() * 1000)
        rows = []
        for feat, w in weights.items():
            s_mean, f_mean = means.get(feat, (0.0, 0.0))
            rows.append(
                {
                    "feature": feat,
                    "success_mean": s_mean,
                    "fail_mean": f_mean,
                    "weight": w,
                    "updated_ts": ts,
                }
            )
        if not rows:
            return
        self.store.execute("DELETE FROM correlations")
        self.store.execute(
            """
            INSERT INTO correlations (feature, success_mean, fail_mean, weight, updated_ts)
            VALUES (:feature, :success_mean, :fail_mean, :weight, :updated_ts)
            """,
            rows,
        )

    def load_correlations(self) -> tuple[dict[str, float], dict[str, tuple[float, float]]] | None:
        df = self.store.query("SELECT feature, weight, success_mean, fail_mean FROM correlations")
        if df.empty:
            return None
        weights: dict[str, float] = {}
        means: dict[str, tuple[float, float]] = {}
        for row in df.to_dict(orient="records"):
            feat = str(row["feature"])
            weights[feat] = float(row["weight"] or 0.0)
            means[feat] = (float(row["success_mean"] or 0.0), float(row["fail_mean"] or 0.0))
        return weights, means

    def log_phase(self, phase: str, note: str) -> None:
        self.store.execute(
            "INSERT INTO phase_log (phase, note, created_ts) VALUES (:p, :n, :t)",
            {"p": phase, "n": note, "t": int(time.time() * 1000)},
        )
