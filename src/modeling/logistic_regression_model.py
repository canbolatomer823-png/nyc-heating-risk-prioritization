from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    fbeta_score,
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

from modeling.risk_features import (
    CATEGORICAL_FEATURES,
    MODEL_INPUT_COLUMNS,
    NUMERIC_FEATURES,
    SCORED_CONTEXT_COLUMNS,
    load_labeled_dataset,
    load_prepared_modeling_table,
)
from project_paths import (
    FINAL_DENSE_PANEL_PATH,
    FINAL_LOGISTIC_COEFFICIENTS_PATH,
    FINAL_LOGISTIC_METRICS_PATH,
    FINAL_LOGISTIC_RANKING_METRICS_PATH,
    FINAL_MODELING_TABLE_PATH,
    FINAL_MODEL_BUNDLE_PATH,
    FINAL_MODEL_METADATA_PATH,
    FINAL_SCORED_CSV_PATH,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
logger = logging.getLogger(__name__)


LOGISTIC_PREPARED_COLUMNS = [
    "calendar_date",
    *SCORED_CONTEXT_COLUMNS,
    "next_day_complaint_count",
    *MODEL_INPUT_COLUMNS,
    "target",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit a temporal logistic regression model for next-day heat complaint risk.")
    parser.add_argument(
        "--input",
        default=str(FINAL_MODELING_TABLE_PATH),
        help="Prepared modeling table CSV path. Falls back to the dense panel if a prepared table is not provided.",
    )
    parser.add_argument(
        "--scored-output",
        default=str(FINAL_SCORED_CSV_PATH),
        help="CSV path for row-level scored outputs.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_LOGISTIC_METRICS_PATH),
        help="Markdown output path for metrics.",
    )
    parser.add_argument(
        "--coefficients-output",
        default=str(FINAL_LOGISTIC_COEFFICIENTS_PATH),
        help="CSV output path for fitted coefficients.",
    )
    parser.add_argument(
        "--ranking-metrics-output",
        default=str(FINAL_LOGISTIC_RANKING_METRICS_PATH),
        help="CSV output path for day-level ranking metrics such as Precision@K.",
    )
    parser.add_argument(
        "--model-output",
        default=str(FINAL_MODEL_BUNDLE_PATH),
        help="Joblib output path for the fitted model bundle.",
    )
    parser.add_argument(
        "--metadata-output",
        default=str(FINAL_MODEL_METADATA_PATH),
        help="JSON output path for model metadata.",
    )
    parser.add_argument(
        "--threshold-beta",
        type=float,
        default=0.5,
        help="Beta parameter for threshold tuning on the threshold-tuning split.",
    )
    parser.add_argument(
        "--model-type",
        choices=["logistic", "xgboost", "lightgbm"],
        default="logistic",
        help="Classifier type to use for the risk model.",
    )
    parser.add_argument(
        "--scale-pos-weight",
        type=float,
        default=None,
        help="Scale positive weight for tree models (default: auto-computed from class ratio).",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=100,
        help="Number of estimators for tree models.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="Maximum tree depth for tree models.",
    )
    return parser.parse_args()


def split_by_date(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    unique_dates = sorted(df["calendar_date"].dropna().dt.strftime("%Y-%m-%d").unique())
    if len(unique_dates) < 5:
        raise ValueError("Need at least 5 labeled dates to create train/validation/test splits.")

    train_cut = max(1, int(len(unique_dates) * 0.6))
    val_cut = min(max(train_cut + 1, int(len(unique_dates) * 0.8)), len(unique_dates) - 1)

    train_dates = unique_dates[:train_cut]
    val_dates = unique_dates[train_cut:val_cut]
    test_dates = unique_dates[val_cut:]

    train_df = df[df["calendar_date"].dt.strftime("%Y-%m-%d").isin(train_dates)].copy()
    val_df = df[df["calendar_date"].dt.strftime("%Y-%m-%d").isin(val_dates)].copy()
    test_df = df[df["calendar_date"].dt.strftime("%Y-%m-%d").isin(test_dates)].copy()
    return train_df, val_df, test_df


def split_validation_window(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_dates = sorted(df["calendar_date"].dropna().dt.strftime("%Y-%m-%d").unique())
    if len(unique_dates) < 2:
        raise ValueError("Need at least 2 validation dates to split calibration and threshold windows.")

    cut = max(1, len(unique_dates) // 2)
    calibration_dates = set(unique_dates[:cut])
    threshold_dates = set(unique_dates[cut:])
    if not threshold_dates:
        calibration_dates = set(unique_dates[:-1])
        threshold_dates = {unique_dates[-1]}

    key_dates = df["calendar_date"].dt.strftime("%Y-%m-%d")
    calibration_df = df[key_dates.isin(calibration_dates)].copy()
    threshold_df = df[key_dates.isin(threshold_dates)].copy()
    return calibration_df, threshold_df


def split_date_windows(unique_dates: list[str]) -> tuple[set[str], set[str], set[str], set[str]]:
    if len(unique_dates) < 5:
        raise ValueError("Need at least 5 labeled dates to create train/validation/test splits.")

    train_cut = max(1, int(len(unique_dates) * 0.6))
    val_cut = min(max(train_cut + 1, int(len(unique_dates) * 0.8)), len(unique_dates) - 1)

    train_dates = set(unique_dates[:train_cut])
    validation_dates = unique_dates[train_cut:val_cut]
    test_dates = set(unique_dates[val_cut:])

    if len(validation_dates) < 2:
        raise ValueError("Need at least 2 validation dates to split calibration and threshold windows.")
    validation_cut = max(1, len(validation_dates) // 2)
    calibration_dates = set(validation_dates[:validation_cut])
    threshold_dates = set(validation_dates[validation_cut:])
    if not threshold_dates:
        calibration_dates = set(validation_dates[:-1])
        threshold_dates = {validation_dates[-1]}

    return train_dates, calibration_dates, threshold_dates, test_dates


def build_classifier(model_type: str = "logistic", **kwargs: Any) -> BaseEstimator:
    if model_type == "logistic":
        return LogisticRegression(max_iter=kwargs.get("max_iter", 1000), class_weight="balanced")
    if model_type == "xgboost":
        import xgboost as xgb
        return xgb.XGBClassifier(
            scale_pos_weight=kwargs.get("scale_pos_weight", 1.0),
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 6),
            learning_rate=kwargs.get("learning_rate", 0.1),
            verbosity=0,
            random_state=42,
        )
    if model_type == "lightgbm":
        import lightgbm as lgb
        return lgb.LGBMClassifier(
            scale_pos_weight=kwargs.get("scale_pos_weight", 1.0),
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 6),
            learning_rate=kwargs.get("learning_rate", 0.1),
            verbose=-1,
            random_state=42,
        )
    raise ValueError(f"Unknown model type: {model_type}")


def build_pipeline(model_type: str = "logistic", **kwargs: Any) -> Pipeline:
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
            ("classifier", build_classifier(model_type=model_type, **kwargs)),
        ]
    )


def logit_feature(probabilities: pd.Series | np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_platt_calibrator(y_true: pd.Series, probabilities: pd.Series) -> LogisticRegression:
    calibrator = LogisticRegression(max_iter=200)
    calibrator.fit(logit_feature(probabilities), y_true.astype(int))
    return calibrator


def apply_calibration(calibrator: LogisticRegression | None, probabilities: pd.Series | np.ndarray) -> np.ndarray:
    raw = np.asarray(probabilities, dtype=float)
    if calibrator is None:
        return raw
    return calibrator.predict_proba(logit_feature(raw))[:, 1]


def select_threshold(y_true: pd.Series, probabilities: pd.Series, beta: float = 1.0) -> float:
    best_threshold = 0.5
    actual_rate = float(y_true.mean())
    best_score: tuple[float, float, float, float] | None = None
    for raw_threshold in range(5, 96, 5):
        threshold = raw_threshold / 100
        predictions = (probabilities >= threshold).astype(int)
        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        fbeta = fbeta_score(y_true, predictions, beta=beta, zero_division=0)
        predicted_rate = float(predictions.mean())
        score = (
            fbeta,
            -abs(predicted_rate - actual_rate),
            precision,
            recall,
        )
        if best_score is None or score > best_score:
            best_threshold = threshold
            best_score = score
    return best_threshold


def compute_metrics(y_true: pd.Series, probabilities: pd.Series, threshold: float) -> dict[str, float | int]:
    predictions = (probabilities >= threshold).astype(int)
    metrics: dict[str, float | int] = {
        "rows": int(len(y_true)),
        "actual_positive_rate": round(float(y_true.mean()), 4),
        "mean_probability": round(float(pd.Series(probabilities).mean()), 4),
        "predicted_positive_rate": round(float(predictions.mean()), 4),
        "accuracy": round(float(accuracy_score(y_true, predictions)), 4),
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 4),
        "average_precision": round(float(average_precision_score(y_true, probabilities)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 4),
    }
    if y_true.nunique() > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, probabilities)), 4)
    else:
        metrics["roc_auc"] = "n/a"
    return metrics


def score_split(
    model: Pipeline,
    calibrator: LogisticRegression | None,
    df: pd.DataFrame,
    split_name: str,
    threshold: float,
) -> pd.DataFrame:
    scored = df
    raw_probabilities = model.predict_proba(scored[MODEL_INPUT_COLUMNS])[:, 1]
    probabilities = apply_calibration(calibrator, raw_probabilities)
    scored["raw_model_probability"] = raw_probabilities
    scored["model_probability"] = probabilities
    scored["model_threshold"] = threshold
    scored["model_prediction"] = (scored["model_probability"] >= threshold).astype(int)
    scored["data_split"] = split_name
    return scored


def coefficient_frame(model: Pipeline) -> pd.DataFrame:
    preprocessor = model.named_steps["preprocess"]
    classifier = model.named_steps["classifier"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_[0]
    return pd.DataFrame({"feature": feature_names, "coefficient": coefficients}).sort_values(
        "coefficient", ascending=False
    )


def normalize_date_value(value: object) -> str:
    if value is None:
        return "n/a"
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def date_range_for(df: pd.DataFrame) -> tuple[object, object]:
    return df["calendar_date"].min(), df["calendar_date"].max()


def date_range_for_dates(dates: set[str]) -> tuple[str, str]:
    ordered = sorted(dates)
    return ordered[0], ordered[-1]


def prepared_input_dates(path: Path) -> list[str]:
    unique_dates: set[str] = set()
    for chunk in pd.read_csv(path, usecols=["calendar_date"], chunksize=250_000):
        parsed = pd.to_datetime(chunk["calendar_date"], errors="coerce")
        unique_dates.update(parsed.dropna().dt.strftime("%Y-%m-%d").unique().tolist())
    return sorted(unique_dates)


def input_is_prepared_modeling_table(path: Path) -> bool:
    if not path.exists():
        return False
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    return "target" in columns and all(column in columns for column in MODEL_INPUT_COLUMNS)


def write_scored_split(path: Path, scored: pd.DataFrame, include_header: bool) -> int:
    scored["calendar_date"] = scored["calendar_date"].dt.strftime("%Y-%m-%d")
    scored.to_csv(
        path,
        index=False,
        mode="w" if include_header else "a",
        header=include_header,
    )
    return int(len(scored))


def compute_daily_ranking_metrics(
    scored: pd.DataFrame,
    ks: tuple[int, ...] = (10, 25, 50, 100),
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    if scored.empty:
        return pd.DataFrame()

    for calendar_date, group in scored.groupby("calendar_date"):
        ordered = group.sort_values("model_probability", ascending=False).reset_index(drop=True)
        actual_positive_rate = float(ordered["target"].mean())
        total_positives = int(ordered["target"].sum())
        for k in ks:
            top_n = min(k, len(ordered))
            top = ordered.head(top_n)
            hits = int(top["target"].sum())
            precision_at_k = float(top["target"].mean()) if top_n else 0.0
            recall_at_k = float(hits / total_positives) if total_positives else 0.0
            lift_at_k = float(precision_at_k / actual_positive_rate) if actual_positive_rate else 0.0
            rows.append(
                {
                    "calendar_date": normalize_date_value(calendar_date),
                    "k": int(k),
                    "rows_available": int(len(ordered)),
                    "actual_positive_rate": round(actual_positive_rate, 6),
                    "positive_hits_at_k": hits,
                    "precision_at_k": round(precision_at_k, 6),
                    "recall_at_k": round(recall_at_k, 6),
                    "lift_at_k": round(lift_at_k, 6),
                    "top_probability_min": round(float(top["model_probability"].min()), 6) if top_n else 0.0,
                    "top_probability_max": round(float(top["model_probability"].max()), 6) if top_n else 0.0,
                }
            )
    return pd.DataFrame(rows)


def summarize_ranking_metrics(ranking_metrics: pd.DataFrame) -> dict[int, dict[str, float | int | str]]:
    summary: dict[int, dict[str, float | int | str]] = {}
    if ranking_metrics.empty:
        return summary

    latest_date = str(ranking_metrics["calendar_date"].max())
    for k, group in ranking_metrics.groupby("k"):
        latest = group[group["calendar_date"] == latest_date].iloc[0]
        summary[int(k)] = {
            "days": int(len(group)),
            "mean_precision_at_k": round(float(group["precision_at_k"].mean()), 4),
            "mean_recall_at_k": round(float(group["recall_at_k"].mean()), 4),
            "mean_lift_at_k": round(float(group["lift_at_k"].mean()), 4),
            "latest_date": latest_date,
            "latest_precision_at_k": round(float(latest["precision_at_k"]), 4),
            "latest_hits_at_k": int(latest["positive_hits_at_k"]),
        }
    return summary


def format_metrics_section(title: str, metrics: dict[str, float | int], date_range: tuple[str, str]) -> list[str]:
    return [
        f"## {title}",
        f"- Date range: {normalize_date_value(date_range[0])} -> {normalize_date_value(date_range[1])}",
        f"- Rows: {metrics['rows']}",
        f"- Actual positive rate: {metrics['actual_positive_rate']}",
        f"- Mean probability: {metrics['mean_probability']}",
        f"- Predicted positive rate: {metrics['predicted_positive_rate']}",
        f"- Accuracy: {metrics['accuracy']}",
        f"- Precision: {metrics['precision']}",
        f"- Recall: {metrics['recall']}",
        f"- F1: {metrics['f1']}",
        f"- Average precision: {metrics['average_precision']}",
        f"- Brier score: {metrics['brier_score']}",
        f"- ROC AUC: {metrics['roc_auc']}",
        "",
    ]


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    prepared_input = input_is_prepared_modeling_table(input_path)

    if prepared_input:
        unique_dates = prepared_input_dates(input_path)
        train_date_set, calibration_date_set, threshold_date_set, test_date_set = split_date_windows(unique_dates)

        train_fit_df = load_prepared_modeling_table(
            input_path,
            columns=LOGISTIC_PREPARED_COLUMNS,
            allowed_dates=train_date_set,
        )
        calibration_df = load_prepared_modeling_table(
            input_path,
            columns=LOGISTIC_PREPARED_COLUMNS,
            allowed_dates=calibration_date_set,
        )
        threshold_df = load_prepared_modeling_table(
            input_path,
            columns=LOGISTIC_PREPARED_COLUMNS,
            allowed_dates=threshold_date_set,
        )

        train_dates = date_range_for_dates(train_date_set)
        calibration_dates = date_range_for_dates(calibration_date_set)
        threshold_dates = date_range_for_dates(threshold_date_set)
        test_dates = date_range_for_dates(test_date_set)
    else:
        fallback_path = input_path if input_path.exists() else FINAL_DENSE_PANEL_PATH
        df = load_labeled_dataset(fallback_path)
        train_fit_df, val_df, test_df = split_by_date(df)
        del df
        calibration_df, threshold_df = split_validation_window(val_df)
        del val_df

        train_dates = date_range_for(train_fit_df)
        calibration_dates = date_range_for(calibration_df)
        threshold_dates = date_range_for(threshold_df)
        test_dates = date_range_for(test_df)

    model_kwargs: dict[str, Any] = {}
    if args.model_type != "logistic":
        neg, pos = np.bincount(train_fit_df["target"].astype(int))
        model_kwargs["scale_pos_weight"] = args.scale_pos_weight if args.scale_pos_weight else neg / pos
        model_kwargs["n_estimators"] = args.n_estimators
        model_kwargs["max_depth"] = args.max_depth
        logger.info("model_type=%s scale_pos_weight=%.1f", args.model_type, model_kwargs["scale_pos_weight"])

    model = build_pipeline(model_type=args.model_type, **model_kwargs)
    model.fit(train_fit_df[MODEL_INPUT_COLUMNS], train_fit_df["target"])
    if prepared_input:
        del train_fit_df

    calibration_raw_probabilities = pd.Series(
        model.predict_proba(calibration_df[MODEL_INPUT_COLUMNS])[:, 1],
        index=calibration_df.index,
    )
    calibrator = fit_platt_calibrator(calibration_df["target"], calibration_raw_probabilities)

    threshold_raw_probabilities = pd.Series(
        model.predict_proba(threshold_df[MODEL_INPUT_COLUMNS])[:, 1],
        index=threshold_df.index,
    )
    threshold_probabilities = pd.Series(
        apply_calibration(calibrator, threshold_raw_probabilities),
        index=threshold_df.index,
    )
    threshold = select_threshold(threshold_df["target"], threshold_probabilities, beta=args.threshold_beta)
    del calibration_raw_probabilities
    del threshold_raw_probabilities
    del threshold_probabilities

    scored_output_path = Path(args.scored_output)
    scored_output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = True

    if prepared_input:
        train_scored = score_split(
            model,
            calibrator,
            load_prepared_modeling_table(input_path, columns=LOGISTIC_PREPARED_COLUMNS, allowed_dates=train_date_set),
            "train",
            threshold,
        )
        calibration_scored = score_split(model, calibrator, calibration_df, "calibration", threshold)
        threshold_scored = score_split(model, calibrator, threshold_df, "threshold_tuning", threshold)
        test_scored = score_split(
            model,
            calibrator,
            load_prepared_modeling_table(input_path, columns=LOGISTIC_PREPARED_COLUMNS, allowed_dates=test_date_set),
            "test",
            threshold,
        )
    else:
        train_scored = score_split(model, calibrator, train_fit_df, "train", threshold)
        calibration_scored = score_split(model, calibrator, calibration_df, "calibration", threshold)
        threshold_scored = score_split(model, calibrator, threshold_df, "threshold_tuning", threshold)
        test_scored = score_split(model, calibrator, test_df, "test", threshold)

    train_metrics = compute_metrics(train_scored["target"], train_scored["model_probability"], threshold)
    write_scored_split(scored_output_path, train_scored, include_header=write_header)
    write_header = False
    del train_scored
    if not prepared_input:
        del train_fit_df

    calibration_metrics = compute_metrics(
        calibration_scored["target"],
        calibration_scored["model_probability"],
        threshold,
    )
    write_scored_split(scored_output_path, calibration_scored, include_header=write_header)
    del calibration_scored
    del calibration_df

    threshold_metrics = compute_metrics(
        threshold_scored["target"],
        threshold_scored["model_probability"],
        threshold,
    )
    write_scored_split(scored_output_path, threshold_scored, include_header=write_header)
    del threshold_scored
    del threshold_df

    test_metrics = compute_metrics(test_scored["target"], test_scored["model_probability"], threshold)
    ranking_metrics = compute_daily_ranking_metrics(test_scored)
    ranking_summary = summarize_ranking_metrics(ranking_metrics)
    write_scored_split(scored_output_path, test_scored, include_header=write_header)
    del test_scored
    if not prepared_input:
        del test_df

    coefficients = coefficient_frame(model)
    coefficients.to_csv(args.coefficients_output, index=False)
    ranking_metrics_output = Path(args.ranking_metrics_output)
    ranking_metrics_output.parent.mkdir(parents=True, exist_ok=True)
    ranking_metrics.to_csv(ranking_metrics_output, index=False)

    positive_coefficients = coefficients[coefficients["coefficient"] > 0].head(8)
    negative_coefficients = coefficients[coefficients["coefficient"] < 0].sort_values("coefficient").head(8)

    lines = [
        "# Logistic Regression Metrics",
        "",
        "## Setup",
        f"- Calibration method: platt",
        f"- Threshold tuning beta: {args.threshold_beta}",
        f"- Threshold selected on threshold-tuning split: {threshold}",
        f"- Numeric features: {', '.join(NUMERIC_FEATURES)}",
        f"- Categorical features: {', '.join(CATEGORICAL_FEATURES)}",
        "",
    ]
    lines.extend(format_metrics_section("Train", train_metrics, train_dates))
    lines.extend(format_metrics_section("Calibration", calibration_metrics, calibration_dates))
    lines.extend(format_metrics_section("Threshold Tuning", threshold_metrics, threshold_dates))
    lines.extend(format_metrics_section("Test", test_metrics, test_dates))
    lines.append("## Top Positive Coefficients")
    for row in positive_coefficients.itertuples(index=False):
        lines.append(f"- {row.feature}: {round(float(row.coefficient), 4)}")
    lines.append("")
    lines.append("## Top Negative Coefficients")
    for row in negative_coefficients.itertuples(index=False):
        lines.append(f"- {row.feature}: {round(float(row.coefficient), 4)}")
    lines.append("")
    lines.append("## Operational Ranking Quality")
    for k in sorted(ranking_summary):
        item = ranking_summary[k]
        lines.append(
            f"- Mean Precision@{k}: {item['mean_precision_at_k']} | "
            f"Mean Recall@{k}: {item['mean_recall_at_k']} | "
            f"Mean Lift@{k}: {item['mean_lift_at_k']}"
        )
        lines.append(
            f"- Latest test day Precision@{k} ({item['latest_date']}): "
            f"{item['latest_precision_at_k']} with {item['latest_hits_at_k']} positive hits"
        )
    lines.append("")
    lines.append("This benchmark now uses validation-window Platt calibration plus a precision-favoring threshold objective.")

    metrics_path = Path(args.metrics_output)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text("\n".join(lines), encoding="utf-8")

    model_path = Path(args.model_output)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = Path(args.metadata_output)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "model_type": "logistic_regression",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "calibration_method": "platt",
        "threshold_beta": args.threshold_beta,
        "threshold": threshold,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "model_input_columns": MODEL_INPUT_COLUMNS,
        "date_ranges": {
            "train": [normalize_date_value(train_dates[0]), normalize_date_value(train_dates[1])],
            "calibration": [normalize_date_value(calibration_dates[0]), normalize_date_value(calibration_dates[1])],
            "threshold_tuning": [normalize_date_value(threshold_dates[0]), normalize_date_value(threshold_dates[1])],
            "test": [normalize_date_value(test_dates[0]), normalize_date_value(test_dates[1])],
        },
        "metrics": {
            "train": train_metrics,
            "calibration": calibration_metrics,
            "threshold_tuning": threshold_metrics,
            "test": test_metrics,
        },
        "ranking_metrics": ranking_summary,
        "feature_names": model.named_steps["preprocess"].get_feature_names_out().tolist(),
    }
    joblib.dump(
        {
            "model": model,
            "calibrator": calibrator,
            "metadata": metadata,
        },
        model_path,
    )
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info("wrote scored output to %s", args.scored_output)
    logger.info("wrote metrics to %s", args.metrics_output)
    logger.info("wrote coefficients to %s", args.coefficients_output)
    logger.info("wrote ranking metrics to %s", args.ranking_metrics_output)
    logger.info("wrote model bundle to %s", args.model_output)
    logger.info("wrote model metadata to %s", args.metadata_output)


if __name__ == "__main__":
    main()
