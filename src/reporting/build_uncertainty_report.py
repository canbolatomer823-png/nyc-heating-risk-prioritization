from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_LOGISTIC_RANKING_METRICS_PATH,
    FINAL_SCORED_CSV_PATH,
    FINAL_STATISTICAL_COEFFICIENTS_PATH,
    FINAL_UNCERTAINTY_REPORT_PATH,
    FINAL_UNCERTAINTY_TABLE_PATH,
)
from reporting.evaluation_utils import bootstrap_mean_ci, load_scored_splits, write_csv


UNCERTAINTY_COLUMNS = [
    "calendar_date",
    "target",
    "model_prediction",
    "model_probability",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap held-out uncertainty intervals for model metrics.")
    parser.add_argument("--input", default=str(FINAL_SCORED_CSV_PATH), help="Scored CSV input path.")
    parser.add_argument(
        "--ranking-input",
        default=str(FINAL_LOGISTIC_RANKING_METRICS_PATH),
        help="Daily ranking metrics CSV input path.",
    )
    parser.add_argument(
        "--coefficients-input",
        default=str(FINAL_STATISTICAL_COEFFICIENTS_PATH),
        help="Statistical coefficient table used for inferential confidence intervals.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_UNCERTAINTY_TABLE_PATH),
        help="CSV output path for bootstrap metric intervals.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_UNCERTAINTY_REPORT_PATH),
        help="Markdown output path for the uncertainty report.",
    )
    parser.add_argument("--n-bootstrap", type=int, default=1000, help="Bootstrap replicate count.")
    parser.add_argument("--random-state", type=int, default=42, help="Bootstrap random seed.")
    return parser.parse_args()


def daily_classification_metrics(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for calendar_date, group in scored.groupby("calendar_date"):
        y_true = group["target"]
        y_pred = group["model_prediction"]
        y_prob = group["model_probability"]
        row: dict[str, object] = {
            "calendar_date": calendar_date,
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "average_precision": float(average_precision_score(y_true, y_prob)),
            "brier_score": float(brier_score_loss(y_true, y_prob)),
        }
        if y_true.nunique() > 1:
            row["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_rows_from_daily(daily: pd.DataFrame, n_boot: int, random_state: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for metric in ["f1", "precision", "recall", "average_precision", "brier_score", "roc_auc"]:
        series = pd.to_numeric(daily[metric], errors="coerce").dropna().to_numpy(dtype=float)
        if series.size == 0:
            continue
        point, boot_mean, low, high = bootstrap_mean_ci(series, n_boot=n_boot, random_state=random_state)
        rows.append(
            {
                "metric_group": "classification",
                "metric": metric,
                "point_estimate": round(point, 6),
                "bootstrap_mean": round(boot_mean, 6),
                "ci_low_95": round(low, 6),
                "ci_high_95": round(high, 6),
                "n_days": int(series.size),
            }
        )
    return rows


def bootstrap_ranking_rows(path: Path, n_boot: int, random_state: int) -> list[dict[str, object]]:
    ranking = pd.read_csv(path)
    rows: list[dict[str, object]] = []
    for k in sorted(ranking["k"].unique()):
        group = ranking[ranking["k"] == k]
        for metric in ["precision_at_k", "recall_at_k", "lift_at_k"]:
            series = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy(dtype=float)
            point, boot_mean, low, high = bootstrap_mean_ci(series, n_boot=n_boot, random_state=random_state)
            rows.append(
                {
                    "metric_group": f"ranking_k_{int(k)}",
                    "metric": metric,
                    "point_estimate": round(point, 6),
                    "bootstrap_mean": round(boot_mean, 6),
                    "ci_low_95": round(low, 6),
                    "ci_high_95": round(high, 6),
                    "n_days": int(series.size),
                }
            )
    return rows


def selected_inference_intervals(path: Path) -> list[dict[str, object]]:
    coefficients = pd.read_csv(path)
    selectors = [
        ("gee_logistic", "cre_vulnerability_index", "gee_cre"),
        ("gee_logistic", "weather_temp_drop_c", "gee_temp_drop"),
        ("gee_logistic", "weather_heating_degree_scaled", "gee_heating_degree"),
        ("negative_binomial", "log1p_current_complaint_count", "nb_current_count"),
    ]
    rows: list[dict[str, object]] = []
    for model, term, label in selectors:
        row = coefficients[(coefficients["model"] == model) & (coefficients["term"] == term)]
        if row.empty:
            continue
        value = row.iloc[0]
        rows.append(
            {
                "metric_group": "inference_interval",
                "metric": label,
                "point_estimate": round(float(value["effect"]), 6),
                "bootstrap_mean": "",
                "ci_low_95": round(float(np.exp(value["conf_low"])), 6),
                "ci_high_95": round(float(np.exp(value["conf_high"])), 6),
                "n_days": "",
            }
        )
    return rows


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    df = pd.DataFrame(rows)
    lines = [
        "# Uncertainty Report",
        "",
        "Held-out classification and ranking metrics are summarized with day-level bootstrap confidence intervals.",
        "",
    ]

    for metric in ["f1", "precision", "recall", "roc_auc", "average_precision", "brier_score"]:
        row = df[(df["metric_group"] == "classification") & (df["metric"] == metric)]
        if row.empty:
            continue
        value = row.iloc[0]
        lines.append(
            f"- {metric}: point `{value['point_estimate']}` | 95% CI `[{value['ci_low_95']}, {value['ci_high_95']}]`"
        )

    lines.extend(["", "## Ranking intervals"])
    for metric_group in ["ranking_k_10", "ranking_k_25", "ranking_k_50"]:
        subset = df[df["metric_group"] == metric_group]
        if subset.empty:
            continue
        label = metric_group.replace("ranking_k_", "K=")
        precision_row = subset[subset["metric"] == "precision_at_k"].iloc[0]
        lift_row = subset[subset["metric"] == "lift_at_k"].iloc[0]
        lines.append(
            f"- {label}: Precision@K `{precision_row['point_estimate']}` with 95% CI `[{precision_row['ci_low_95']}, {precision_row['ci_high_95']}]`; "
            f"Lift@K `{lift_row['point_estimate']}` with 95% CI `[{lift_row['ci_low_95']}, {lift_row['ci_high_95']}]`"
        )

    inference = df[df["metric_group"] == "inference_interval"]
    if not inference.empty:
        lines.extend(["", "## Selected inference intervals"])
        for row in inference.to_dict(orient="records"):
            lines.append(
                f"- {row['metric']}: effect `{row['point_estimate']}` with interval `[{row['ci_low_95']}, {row['ci_high_95']}]`"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    scored = load_scored_splits(Path(args.input), UNCERTAINTY_COLUMNS, {"test"})
    if scored.empty:
        raise ValueError("No test rows were found in the scored CSV.")

    for column in ["target", "model_prediction", "model_probability"]:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0)
    scored["calendar_date"] = pd.to_datetime(scored["calendar_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    daily = daily_classification_metrics(scored)
    rows = bootstrap_rows_from_daily(daily, args.n_bootstrap, args.random_state)
    rows.extend(bootstrap_ranking_rows(Path(args.ranking_input), args.n_bootstrap, args.random_state))
    rows.extend(selected_inference_intervals(Path(args.coefficients_input)))

    write_csv(Path(args.metrics_output), rows)
    write_report(Path(args.report_output), rows)

    print(f"wrote uncertainty metrics to {args.metrics_output}", flush=True)
    print(f"wrote uncertainty report to {args.report_output}", flush=True)


if __name__ == "__main__":
    main()
