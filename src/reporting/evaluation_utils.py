from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score


def safe_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def safe_int(value: object) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def load_scored_splits(
    path: Path,
    usecols: Iterable[str],
    allowed_splits: set[str],
    chunksize: int = 250_000,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    selected = set(usecols) | {"data_split"}
    for chunk in pd.read_csv(
        path,
        usecols=lambda column: column in selected,
        chunksize=chunksize,
        low_memory=False,
    ):
        filtered = chunk[chunk["data_split"].isin(allowed_splits)].copy()
        if not filtered.empty:
            frames.append(filtered)
    if not frames:
        return pd.DataFrame(columns=list(selected))
    return pd.concat(frames, ignore_index=True)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def classification_metrics(y_true: pd.Series, y_pred: pd.Series, y_prob: pd.Series | None = None) -> dict[str, float]:
    metrics = {
        "actual_positive_rate": float(y_true.mean()),
        "predicted_positive_rate": float(y_pred.mean()),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if y_prob is not None:
        metrics["average_precision"] = float(average_precision_score(y_true, y_prob))
        metrics["brier_score"] = float(brier_score_loss(y_true, y_prob))
        metrics["mean_probability"] = float(y_prob.mean())
        if y_true.nunique() > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    return metrics


def bootstrap_mean_ci(values: np.ndarray, n_boot: int = 1000, random_state: int = 42) -> tuple[float, float, float, float]:
    if values.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    rng = np.random.default_rng(random_state)
    samples = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        draws = rng.choice(values, size=len(values), replace=True)
        samples[index] = draws.mean()
    point = float(values.mean())
    return (
        point,
        float(samples.mean()),
        float(np.quantile(samples, 0.025)),
        float(np.quantile(samples, 0.975)),
    )
