"""Model evaluation utilities.

These evaluation routines operate on legally sourced public datasets. Ensure
that upstream pipelines comply with robots.txt directives, rate limits, and
platform Terms of Service. Remove or anonymize any personal data before
analysis."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn import metrics


def precision_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    order = np.argsort(y_scores)[::-1][:k]
    top_k_true = y_true[order]
    return float(np.mean(top_k_true))


def ndcg_score(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    ideal = metrics.ndcg_score(y_true.reshape(1, -1), y_scores.reshape(1, -1), k=k)
    return float(ideal)


def playback_curve(y_true: np.ndarray, y_scores: np.ndarray, bins: int = 20) -> pd.DataFrame:
    """Compute cumulative gain style playback curve data."""
    order = np.argsort(y_scores)[::-1]
    sorted_true = y_true[order]
    cumulative_positive = np.cumsum(sorted_true)
    cumulative_ratio = cumulative_positive / cumulative_positive[-1] if cumulative_positive[-1] > 0 else cumulative_positive
    population_ratio = np.arange(1, len(sorted_true) + 1) / len(sorted_true)
    step = max(len(sorted_true) // bins, 1)
    indices = np.arange(step - 1, len(sorted_true), step)
    curve = pd.DataFrame(
        {
            "population_ratio": population_ratio[indices],
            "cumulative_positive_ratio": cumulative_ratio[indices],
        }
    )
    return curve


def evaluate_predictions(
    y_true: np.ndarray, y_scores: np.ndarray, y_pred: np.ndarray, k: int = 20
) -> Tuple[Dict[str, float], pd.DataFrame]:
    auc = metrics.roc_auc_score(y_true, y_scores)
    precision = precision_at_k(y_true, y_scores, k)
    ndcg = ndcg_score(y_true, y_scores, k)
    accuracy = metrics.accuracy_score(y_true, y_pred)
    curve = playback_curve(y_true, y_scores)
    metrics_dict = {
        "auc": float(auc),
        "precision_at_k": precision,
        "ndcg_at_k": ndcg,
        "accuracy": float(accuracy),
    }
    return metrics_dict, curve


__all__ = ["evaluate_predictions", "precision_at_k", "ndcg_score", "playback_curve"]
