from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.logistic_regression_model import select_threshold
from modeling.risk_features import CATEGORICAL_FEATURES, MODEL_INPUT_COLUMNS, NUMERIC_FEATURES, prepare_feature_frame
from project_paths import FINAL_DENSE_PANEL_PATH, FINAL_REPORTS_DIR


@dataclass(frozen=True)
class Fold:
    fold_id: int
    train_months: list[str]
    validation_month: str
    test_month: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run expanding-window monthly backtests for the NYC heating complaint risk model."
    )
    parser.add_argument(
        "--input",
        default=str(FINAL_DENSE_PANEL_PATH),
        help="Dense panel CSV path.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_REPORTS_DIR / "rolling_backtest_metrics.csv"),
        help="CSV output path for fold-level metrics.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(FINAL_REPORTS_DIR / "rolling_backtest_summary.md"),
        help="Markdown output path for the backtest summary.",
    )
    parser.add_argument("--chunksize", type=int, default=250_000, help="CSV chunk size.")
    parser.add_argument(
        "--min-train-months",
        type=int,
        default=2,
        help="Minimum number of months before the validation month.",
    )
    parser.add_argument(
        "--negative-ratio",
        type=int,
        default=5,
        help="Maximum sampled negative rows per positive training row.",
    )
    parser.add_argument(
        "--max-train-rows",
        type=int,
        default=500_000,
        help="Maximum sampled rows used to fit each fold's logistic model.",
    )
    parser.add_argument("--random-state", type=int, default=42, help="Deterministic sampling seed.")
    parser.add_argument(
        "--logistic-max-iter",
        type=int,
        default=250,
        help="Maximum iterations for fold-level SGD logistic regression fits.",
    )
    return parser.parse_args()


def build_backtest_pipeline(max_iter: int, random_state: int) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    class_weight="balanced",
                    max_iter=max_iter,
                    tol=1e-3,
                    random_state=random_state,
                ),
            ),
        ]
    )


def iter_prepared_chunks(path: Path, chunksize: int):
    for chunk in pd.read_csv(path, chunksize=chunksize, dtype=str):
        if "next_day_label_available" not in chunk.columns:
            raise ValueError("Expected next_day_label_available in dense panel.")
        label_available = pd.to_numeric(chunk["next_day_label_available"], errors="coerce").fillna(0).astype(int)
        chunk = chunk[label_available == 1].copy()
        if chunk.empty:
            continue
        prepared = prepare_feature_frame(chunk, compute_target=True)
        prepared["month"] = prepared["calendar_date"].dt.strftime("%Y-%m")
        yield prepared


def discover_months(path: Path, chunksize: int) -> list[str]:
    months: set[str] = set()
    for chunk in pd.read_csv(
        path,
        usecols=["calendar_date", "next_day_label_available"],
        chunksize=chunksize,
        dtype=str,
    ):
        label_available = pd.to_numeric(chunk["next_day_label_available"], errors="coerce").fillna(0).astype(int)
        chunk = chunk[label_available == 1].copy()
        if chunk.empty:
            continue
        dates = pd.to_datetime(chunk["calendar_date"], errors="coerce")
        months.update(dates.dropna().dt.strftime("%Y-%m").unique().tolist())
    return sorted(months)


def build_folds(months: list[str], min_train_months: int) -> list[Fold]:
    folds: list[Fold] = []
    fold_id = 1
    for validation_index in range(min_train_months, len(months) - 1):
        folds.append(
            Fold(
                fold_id=fold_id,
                train_months=months[:validation_index],
                validation_month=months[validation_index],
                test_month=months[validation_index + 1],
            )
        )
        fold_id += 1
    return folds


def sample_training_chunk(
    chunk: pd.DataFrame,
    negative_ratio: int,
    random_state: int,
) -> pd.DataFrame:
    positives = chunk[chunk["target"] == 1]
    negatives = chunk[chunk["target"] == 0]
    if positives.empty:
        return negatives.sample(n=min(len(negatives), 1_000), random_state=random_state) if not negatives.empty else chunk
    negative_count = min(len(negatives), max(len(positives) * negative_ratio, 1_000))
    sampled_negatives = negatives.sample(n=negative_count, random_state=random_state) if negative_count else negatives.head(0)
    return pd.concat([positives, sampled_negatives], ignore_index=True)


def limit_training_rows(df: pd.DataFrame, max_rows: int, negative_ratio: int, random_state: int) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    positives = df[df["target"] == 1]
    negatives = df[df["target"] == 0]
    if positives.empty or negatives.empty:
        return df.sample(n=max_rows, random_state=random_state)
    target_positive_cap = max(1, max_rows // max(negative_ratio + 1, 2))
    positive_cap = min(len(positives), target_positive_cap)
    negative_cap = min(len(negatives), max_rows - positive_cap)
    if positive_cap < target_positive_cap and len(negatives) > negative_cap:
        negative_cap = min(len(negatives), max_rows - positive_cap)
    if negative_cap == 0 and len(negatives) > 0:
        positive_cap = min(len(positives), max_rows - 1)
        negative_cap = 1
    sampled_positives = positives.sample(n=positive_cap, random_state=random_state)
    sampled_negatives = negatives.sample(n=negative_cap, random_state=random_state + 1)
    return pd.concat([sampled_positives, sampled_negatives], ignore_index=True)


def collect_fold_frame(
    path: Path,
    fold: Fold,
    months: set[str],
    chunksize: int,
    negative_ratio: int | None,
    max_train_rows: int | None,
    random_state: int,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for chunk_index, chunk in enumerate(iter_prepared_chunks(path, chunksize)):
        selected = chunk[chunk["month"].isin(months)].copy()
        if selected.empty:
            continue
        if negative_ratio is not None:
            selected = sample_training_chunk(selected, negative_ratio, random_state + fold.fold_id + chunk_index)
        frames.append(selected)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    if max_train_rows is not None:
        combined = limit_training_rows(combined, max_train_rows, negative_ratio or 1, random_state + fold.fold_id)
    return combined


def baseline_scores(df: pd.DataFrame) -> pd.Series:
    units = pd.to_numeric(df["unit_count_proxy"], errors="coerce").fillna(0)
    days_since_last = pd.to_numeric(df["days_since_last_complaint"], errors="coerce").fillna(-1)
    score = pd.Series(0.0, index=df.index)
    score += (df["complaint_count"].clip(lower=0) / 2.0).clip(upper=1.0) * 0.22
    score += (df["unique_request_count"].clip(lower=0) / 2.0).clip(upper=1.0) * 0.05
    score += (df["rolling_3d_complaints"].clip(lower=0) / 4.0).clip(upper=1.0) * 0.18
    score += (df["rolling_7d_complaints"].clip(lower=0) / 7.0).clip(upper=1.0) * 0.14
    score += (df["lag_1_complaints"].clip(lower=0) / 2.0).clip(upper=1.0) * 0.08
    score += (df["cumulative_complaints_prior"].clip(lower=0) / 10.0).clip(upper=1.0) * 0.08
    score += (df["complaint_day_count_prior"].clip(lower=0) / 5.0).clip(upper=1.0) * 0.04
    score += (df["prior_max_daily_complaints"].clip(lower=0) / 3.0).clip(upper=1.0) * 0.04
    score += (df["open_linked_violation_count"].clip(lower=0) / 50.0).clip(upper=1.0) * 0.07
    score += (df["heat_sensor_active_flag"] >= 1).astype(float) * 0.05
    score += ((days_since_last >= 0) & (days_since_last <= 2)).astype(float) * 0.03
    score += (df["weather_heating_degree_c"].clip(lower=0) / 10.0).clip(upper=1.0) * 0.04
    score += (df["weather_freezing_any_flag"] >= 1).astype(float) * 0.04
    score += (df["weather_cold_shock_flag"] >= 1).astype(float) * 0.03
    score += (df["weather_temp_drop_c"].clip(lower=0) / 5.0).clip(upper=1.0) * 0.03
    score += (units >= 50).astype(float) * 0.01
    score += df["registration_active_flag"].clip(lower=0, upper=1) * 0.01
    return score.clip(lower=0, upper=1)


def threshold_grid() -> list[float]:
    return [raw / 100 for raw in range(10, 91, 5)]


def select_threshold_from_scores(y_true: pd.Series, scores: pd.Series) -> float:
    best_threshold = 0.5
    best_score: tuple[float, float, float] | None = None
    for threshold in threshold_grid():
        predictions = (scores >= threshold).astype(int)
        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        f1 = f1_score(y_true, predictions, zero_division=0)
        score = (f1, recall, precision)
        if best_score is None or score > best_score:
            best_threshold = threshold
            best_score = score
    return best_threshold


def metrics_from_scores(y_true: pd.Series, scores: pd.Series, threshold: float) -> dict[str, float | int | str]:
    predictions = (scores >= threshold).astype(int)
    metrics: dict[str, float | int | str] = {
        "rows": int(len(y_true)),
        "actual_positive_rate": round(float(y_true.mean()), 6),
        "predicted_positive_rate": round(float(predictions.mean()), 6),
        "accuracy": round(float(accuracy_score(y_true, predictions)), 6),
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 6),
        "average_precision": round(float(average_precision_score(y_true, scores)), 6),
    }
    metrics["roc_auc"] = round(float(roc_auc_score(y_true, scores)), 6) if y_true.nunique() > 1 else "n/a"
    return metrics


def evaluate_model_on_month(
    path: Path,
    month: str,
    chunksize: int,
    model,
    threshold: float,
    model_name: str,
) -> dict[str, float | int | str]:
    y_values: list[np.ndarray] = []
    score_values: list[np.ndarray] = []
    for chunk in iter_prepared_chunks(path, chunksize):
        selected = chunk[chunk["month"] == month].copy()
        if selected.empty:
            continue
        y_values.append(selected["target"].to_numpy())
        if model_name == "baseline":
            score_values.append(baseline_scores(selected).to_numpy())
        else:
            score_values.append(model.predict_proba(selected[MODEL_INPUT_COLUMNS])[:, 1])
    if not y_values:
        return {"rows": 0, "actual_positive_rate": 0, "predicted_positive_rate": 0, "accuracy": 0, "precision": 0, "recall": 0, "f1": 0, "average_precision": 0, "roc_auc": "n/a"}
    y_true = pd.Series(np.concatenate(y_values))
    scores = pd.Series(np.concatenate(score_values))
    return metrics_from_scores(y_true, scores, threshold)


def fold_to_rows(
    path: Path,
    fold: Fold,
    chunksize: int,
    negative_ratio: int,
    max_train_rows: int,
    logistic_max_iter: int,
    random_state: int,
) -> list[dict[str, float | int | str]]:
    print(f"running fold {fold.fold_id}: train={fold.train_months} val={fold.validation_month} test={fold.test_month}", flush=True)
    train_df = collect_fold_frame(
        path,
        fold,
        set(fold.train_months),
        chunksize,
        negative_ratio=negative_ratio,
        max_train_rows=max_train_rows,
        random_state=random_state,
    )
    validation_df = collect_fold_frame(
        path,
        fold,
        {fold.validation_month},
        chunksize,
        negative_ratio=None,
        max_train_rows=None,
        random_state=random_state,
    )
    if train_df.empty or validation_df.empty:
        raise ValueError(f"Fold {fold.fold_id} has empty train or validation data.")

    logistic_model = build_backtest_pipeline(max_iter=logistic_max_iter, random_state=random_state + fold.fold_id)
    logistic_model.fit(train_df[MODEL_INPUT_COLUMNS], train_df["target"])
    validation_probabilities = pd.Series(logistic_model.predict_proba(validation_df[MODEL_INPUT_COLUMNS])[:, 1], index=validation_df.index)
    logistic_threshold = select_threshold(validation_df["target"], validation_probabilities)

    baseline_validation_scores = baseline_scores(validation_df)
    baseline_threshold = select_threshold_from_scores(validation_df["target"], baseline_validation_scores)

    rows: list[dict[str, float | int | str]] = []
    for model_name, model, threshold in [
        ("baseline", None, baseline_threshold),
        ("sgd_logistic_regression", logistic_model, logistic_threshold),
    ]:
        validation_metrics = (
            metrics_from_scores(validation_df["target"], baseline_validation_scores, threshold)
            if model_name == "baseline"
            else metrics_from_scores(validation_df["target"], validation_probabilities, threshold)
        )
        test_metrics = evaluate_model_on_month(path, fold.test_month, chunksize, model, threshold, model_name)

        for split_name, metrics in [("validation", validation_metrics), ("test", test_metrics)]:
            row: dict[str, float | int | str] = {
                "fold_id": fold.fold_id,
                "model": model_name,
                "split": split_name,
                "train_start_month": fold.train_months[0],
                "train_end_month": fold.train_months[-1],
                "validation_month": fold.validation_month,
                "test_month": fold.test_month,
                "train_rows_sampled": int(len(train_df)),
                "train_positive_rate_sampled": round(float(train_df["target"].mean()), 6),
                "threshold": round(float(threshold), 6),
            }
            row.update(metrics)
            rows.append(row)
    return rows


def write_summary(metrics_df: pd.DataFrame, summary_path: Path, source_path: Path, folds: list[Fold]) -> None:
    lines = [
        "# Rolling Backtest Summary",
        "",
        "## Setup",
        f"- Source panel: `{source_path}`",
        f"- Fold count: {len(folds)}",
        "- Scheme: expanding monthly window; threshold tuned on the validation month; final score reported on the following test month.",
        "- SGD logistic regression uses sampled training rows to keep the full heat-season backtest tractable; validation and test metrics are measured on full monthly panels.",
        "",
        "## Test Metrics By Model",
    ]
    test_df = metrics_df[metrics_df["split"] == "test"].copy()
    for model_name, group in test_df.groupby("model"):
        lines.extend(
            [
                f"### {model_name}",
                f"- Mean F1: {group['f1'].mean():.4f}",
                f"- Mean ROC AUC: {pd.to_numeric(group['roc_auc'], errors='coerce').mean():.4f}",
                f"- Mean average precision: {group['average_precision'].mean():.4f}",
                f"- Mean precision: {group['precision'].mean():.4f}",
                f"- Mean recall: {group['recall'].mean():.4f}",
                "",
            ]
        )

    lines.append("## Fold Details")
    for row in test_df.sort_values(["fold_id", "model"]).itertuples(index=False):
        lines.append(
            f"- Fold {row.fold_id} `{row.model}` test `{row.test_month}`: "
            f"F1={row.f1:.4f}, ROC AUC={row.roc_auc}, AP={row.average_precision:.4f}, "
            f"precision={row.precision:.4f}, recall={row.recall:.4f}, rows={int(row.rows)}"
        )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    months = discover_months(input_path, args.chunksize)
    folds = build_folds(months, args.min_train_months)
    if not folds:
        raise ValueError("No valid backtest folds could be built.")

    all_rows: list[dict[str, float | int | str]] = []
    for fold in folds:
        all_rows.extend(
            fold_to_rows(
                input_path,
                fold,
                args.chunksize,
                args.negative_ratio,
                args.max_train_rows,
                args.logistic_max_iter,
                args.random_state,
            )
        )

    metrics_df = pd.DataFrame(all_rows)
    metrics_path = Path(args.metrics_output)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(metrics_path, index=False)
    write_summary(metrics_df, Path(args.summary_output), input_path, folds)
    print(f"wrote rolling backtest metrics to {metrics_path}", flush=True)
    print(f"wrote rolling backtest summary to {args.summary_output}", flush=True)


if __name__ == "__main__":
    main()
