from __future__ import annotations

from dataclasses import dataclass, field
from math import exp

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


FEATURE_ORDER = ["rsi14", "ema_trend", "vol_z", "ret_12", "atr_pct", "fib_ratio", "confluence"]


@dataclass
class FeatureCorrelator:
    scaler: StandardScaler = field(default_factory=StandardScaler)
    model: LogisticRegression | None = None
    weights: dict[str, float] = field(default_factory=dict)
    means: dict[str, tuple[float, float]] = field(default_factory=dict)
    trained: bool = False

    def fit(self, rows: list[dict[str, float]], labels: list[int]) -> dict[str, float]:
        if len(rows) < 30 or len(set(labels)) < 2:
            self.trained = False
            return {}
        x = np.array([[float(r.get(k, 0.0) or 0.0) for k in FEATURE_ORDER] for r in rows], dtype=float)
        y = np.array(labels, dtype=int)
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        self.scaler = StandardScaler()
        xs = self.scaler.fit_transform(x)
        self.model = LogisticRegression(max_iter=400, class_weight="balanced")
        self.model.fit(xs, y)
        coef = self.model.coef_[0]
        mag = np.abs(coef).sum() or 1.0
        self.weights = {k: float(c / mag) for k, c in zip(FEATURE_ORDER, coef)}
        self.means = {}
        for i, k in enumerate(FEATURE_ORDER):
            pos = x[y == 1, i]
            neg = x[y == 0, i]
            self.means[k] = (
                float(pos.mean()) if len(pos) else 0.0,
                float(neg.mean()) if len(neg) else 0.0,
            )
        self.trained = True
        return self.weights

    def load_state(
        self,
        weights: dict[str, float],
        means: dict[str, tuple[float, float]],
    ) -> None:
        self.weights = dict(weights or {})
        self.means = dict(means or {})
        self.model = None
        self.trained = bool(self.weights)

    def _sigmoid_score(self, row: dict[str, float]) -> float:
        z = 0.0
        for key in FEATURE_ORDER:
            z += float(self.weights.get(key, 0.0)) * float(row.get(key, 0.0) or 0.0)
        z = max(-20.0, min(20.0, z))
        return float(1.0 / (1.0 + exp(-z)))

    def predict_proba(self, row: dict[str, float]) -> float | None:
        if not self.trained:
            return None
        if self.model is not None:
            x = np.array([[float(row.get(k, 0.0) or 0.0) for k in FEATURE_ORDER]], dtype=float)
            x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
            xs = self.scaler.transform(x)
            return float(self.model.predict_proba(xs)[0, 1])
        if self.weights:
            return self._sigmoid_score(row)
        return None
