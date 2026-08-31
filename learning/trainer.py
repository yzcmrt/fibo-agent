from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any

import pandas as pd

from analysis.features import build_feature_row
from analysis.path_stats import outcome_path_stats
from analysis.fibonacci import grids_from_pivots
from analysis.indicators import add_indicators
from analysis.pivots import detect_pivots
from learning.correlator import FeatureCorrelator
from learning.memory import LearningMemory
from learning.outcome import label_fib_hold


def _gid(params: dict[str, Any], generation: int) -> str:
    raw = json.dumps({"g": generation, "p": params}, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def default_genome(settings: dict[str, Any]) -> dict[str, Any]:
    piv = settings["pivots"]
    learn = settings["learning"]
    return {
        "method": "pct",
        "threshold": float(piv["short_pct"]),
        "key_ratio": 0.618,
        "horizon_bars": int(learn["horizon_bars"]),
        "touch_tolerance_atr": float(settings["fibonacci"]["touch_tolerance_atr"]),
        "min_continuation_r": float(learn["min_continuation_r"]),
        "atr_period": int(piv["atr_period"]),
        "min_leg_pct": 0.04,
    }


def mutate(params: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    child = copy.deepcopy(params)
    child["method"] = rng.choice(["pct", "atr"])
    if child["method"] == "pct":
        child["threshold"] = round(min(0.12, max(0.015, child["threshold"] * rng.uniform(0.7, 1.4))), 4)
        if child["threshold"] > 0.2:
            child["threshold"] = rng.choice([0.02, 0.03, 0.05, 0.08])
    else:
        base = child["threshold"] if child["threshold"] >= 0.8 else 2.0
        child["threshold"] = round(min(5.0, max(0.8, base * rng.uniform(0.7, 1.4))), 3)
    child["key_ratio"] = rng.choice([0.382, 0.5, 0.618, 0.786])
    child["touch_tolerance_atr"] = round(min(0.6, max(0.1, child["touch_tolerance_atr"] * rng.uniform(0.8, 1.25))), 3)
    child["min_continuation_r"] = round(min(2.0, max(0.6, child["min_continuation_r"] * rng.uniform(0.85, 1.2))), 2)
    child["min_leg_pct"] = round(min(0.12, max(0.02, float(child.get("min_leg_pct", 0.04)) * rng.uniform(0.75, 1.35))), 4)
    return child


def evaluate_genome(df: pd.DataFrame, params: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]], list[int]]:
    work = add_indicators(df)
    pivots = detect_pivots(
        work,
        method=params["method"],
        threshold=float(params["threshold"]),
        atr_period=int(params.get("atr_period", 14)),
    )
    grids = grids_from_pivots(pivots, last_n_legs=max(8, len(pivots)))
    rows: list[dict[str, Any]] = []
    labels: list[int] = []
    successes = 0
    touched = 0
    r_sum = 0.0
    for grid in grids:
        if grid.end.index < 60:
            continue
        if grid.range / max(grid.end.price, 1e-9) < float(params.get("min_leg_pct", 0.02)):
            continue
        out = label_fib_hold(
            work,
            grid,
            key_ratio=float(params["key_ratio"]),
            horizon_bars=int(params["horizon_bars"]),
            touch_tolerance_atr=float(params["touch_tolerance_atr"]),
            min_continuation_r=float(params["min_continuation_r"]),
        )
        if not out.touched:
            continue
        touched += 1
        feats = build_feature_row(
            work,
            min(grid.end.index, len(work) - 1),
            grid=grid,
            fib_ratio=float(params["key_ratio"]),
        )
        feats["confluence"] = 0.0
        feats.update(
            outcome_path_stats(
                work,
                grid,
                key_ratio=float(params["key_ratio"]),
                horizon_bars=int(params["horizon_bars"]),
                entry_price=out.entry_price,
            )
        )
        rows.append(feats)
        labels.append(1 if out.success else 0)
        if out.success:
            successes += 1
        r_sum += out.r_multiple
        feats["_r"] = float(out.r_multiple)
        feats["_mfe"] = float(out.mfe)
        feats["_mae"] = float(out.mae)

    n = touched
    precision = successes / n if n else 0.0
    # recall proxy: successes / all completed legs that had a chance
    recall = successes / max(len(grids), 1)
    avg_r = r_sum / n if n else 0.0
    # fitness rewards precision near the 80% target, sample size, and expectancy
    size_term = min(1.0, n / 80.0)
    precision_term = precision
    r_term = max(0.0, min(avg_r, 2.0)) / 2.0
    penalty = 0.0 if n >= 20 else 0.25 * (1.0 - n / 20.0)
    density = n / max(len(work), 1)
    if density > 0.04:
        penalty += min(0.35, (density - 0.04) * 4.0)
    fitness = 0.62 * precision_term + 0.20 * r_term + 0.18 * size_term - penalty
    metrics = {
        "precision": precision,
        "recall": recall,
        "avg_r": avg_r,
        "n_signals": float(n),
        "n_grids": float(len(grids)),
        "fitness": fitness,
    }
    return metrics, rows, labels


def walk_forward_metrics(df: pd.DataFrame, params: dict[str, Any], folds: int = 4) -> dict[str, float]:
    n = len(df)
    if n < 400 or folds < 2:
        metrics, _, _ = evaluate_genome(df, params)
        return metrics
    fold_len = n // (folds + 1)
    precs = []
    fits = []
    ns = []
    rs = []
    for i in range(folds):
        start = i * fold_len
        end = min(n, start + fold_len * 2)
        chunk = df.iloc[start:end]
        m, _, _ = evaluate_genome(chunk, params)
        precs.append(m["precision"])
        fits.append(m["fitness"])
        ns.append(m["n_signals"])
        rs.append(m["avg_r"])
    n_mean = sum(ns) / max(len(ns), 1)
    return {
        "precision": sum(precs) / len(precs),
        "recall": 0.0,
        "avg_r": sum(rs) / len(rs),
        "n_signals": n_mean,
        "n_grids": 0.0,
        "fitness": sum(fits) / len(fits),
    }


@dataclass
class EvolutionaryTrainer:
    settings: dict[str, Any]
    memory: LearningMemory
    correlator: FeatureCorrelator

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        learn = self.settings["learning"]
        rng = random.Random(int(learn.get("random_seed", 42)))
        pop_n = int(learn["population"])
        gens = int(learn["generations"])
        elite_n = max(2, int(pop_n * float(learn["elite_frac"])))
        folds = int(learn["walk_forward_folds"])

        population = [default_genome(self.settings)]
        while len(population) < pop_n:
            population.append(mutate(default_genome(self.settings), rng))

        history: list[dict[str, Any]] = []
        all_rows: list[dict[str, Any]] = []
        all_labels: list[int] = []
        best: dict[str, Any] | None = None

        for gen in range(gens):
            scored = []
            for params in population:
                metrics = walk_forward_metrics(df, params, folds=folds)
                _, rows, labels = evaluate_genome(df, params)
                all_rows.extend(rows)
                all_labels.extend(labels)
                item = {"params": params, "metrics": metrics, "id": _gid(params, gen)}
                scored.append(item)
                self.memory.save_genome(item["id"], gen, params, metrics)
            scored.sort(key=lambda x: x["metrics"]["fitness"], reverse=True)
            if best is None or scored[0]["metrics"]["fitness"] > best["metrics"]["fitness"]:
                best = scored[0]
            history.append(
                {
                    "generation": gen,
                    "best_fitness": scored[0]["metrics"]["fitness"],
                    "best_precision": scored[0]["metrics"]["precision"],
                    "best_params": scored[0]["params"],
                }
            )
            elites = [copy.deepcopy(s["params"]) for s in scored[:elite_n]]
            population = elites[:]
            while len(population) < pop_n:
                parent = rng.choice(elites)
                population.append(mutate(parent, rng))

        from learning.human_labels import apply_human_overrides, reviews_from_store

        human_hits = 0
        store = getattr(self.memory, "store", None)
        if store is not None:
            reviews = reviews_from_store(store)
            all_rows, all_labels, human_hits = apply_human_overrides(all_rows, all_labels, reviews)
        weights = self.correlator.fit(all_rows, all_labels)
        if weights:
            self.memory.save_correlations(weights, self.correlator.means)

        target = float(learn["target_precision"])
        gate = {
            "target_precision": target,
            "reached": bool(best and best["metrics"]["precision"] >= target and best["metrics"]["n_signals"] >= learn["min_labeled_setups"]),
            "note": (
                "Hedef istatistiksel bir kapıdır; canlı işlem izni değildir. "
                "%80 precision walk-forward + yeterli örneklem olmadan iddia edilmemelidir."
            ),
        }
        return {
            "best": best,
            "history": history,
            "weights": weights,
            "gate": gate,
            "n_labeled": len(all_labels),
            "human_overrides": human_hits,
        }
