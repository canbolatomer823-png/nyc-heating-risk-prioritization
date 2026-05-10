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
    FINAL_FAIRNESS_CALIBRATION_PATH,
    FINAL_FAIRNESS_REPORT_PATH,
    FINAL_FAIRNESS_SEGMENTS_PATH,
    FINAL_SCORED_CSV_PATH,
)
from reporting.evaluation_utils import load_scored_splits, write_csv


FAIRNESS_COLUMNS = [
    "calendar_date",
    "target",
    "model_prediction",
    "model_probability",
    "borough",
    "management_program",
    "cre_vulnerability_index",
    "cre_coverage_flag",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build subgroup fairness and calibration report on held-out predictions.")
    parser.add_argument("--input", default=str(FINAL_SCORED_CSV_PATH), help="Scored CSV input path.")
    parser.add_argument(
        "--segments-output",
        default=str(FINAL_FAIRNESS_SEGMENTS_PATH),
        help="CSV output path for subgroup fairness metrics.",
    )
    parser.add_argument(
        "--calibration-output",
        default=str(FINAL_FAIRNESS_CALIBRATION_PATH),
        help="CSV output path for subgroup calibration bins.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_FAIRNESS_REPORT_PATH),
        help="Markdown output path for subgroup fairness report.",
    )
    parser.add_argument("--min-group-rows", type=int, default=500, help="Minimum held-out rows per subgroup to report.")
    parser.add_argument("--n-bins", type=int, default=10, help="Calibration bin count per subgroup.")
    return parser.parse_args()


def build_cre_bucket(series: pd.Series, coverage: pd.Series) -> pd.Series:
    valid_mask = coverage.fillna(0).astype(int) == 1
    result = pd.Series(["missing"] * len(series), index=series.index, dtype="object")
    valid = series[valid_mask].fillna(0)
    if valid.empty:
        return result
    try:
        bucket = pd.qcut(valid.rank(method="first"), q=3, labels=["low", "mid", "high"])
    except ValueError:
        bucket = pd.Series(["mid"] * len(valid), index=valid.index, dtype="object")
    result.loc[valid.index] = bucket.astype(str)
    return result


def safe_average_precision(y_true: pd.Series, y_prob: pd.Series) -> float:
    if int(y_true.sum()) == 0:
        return 0.0
    return float(average_precision_score(y_true, y_prob))


def safe_roc_auc(y_true: pd.Series, y_prob: pd.Series) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def build_calibration_bins(group: pd.DataFrame, n_bins: int) -> tuple[list[dict[str, object]], float, float]:
    local = group[["target", "model_probability"]].copy().sort_values("model_probability").reset_index(drop=True)
    if local.empty:
        return [], 0.0, 0.0
    local["bin_index"] = pd.qcut(
        local.index + 1,
        q=min(n_bins, len(local)),
        labels=False,
        duplicates="drop",
    )
    bins: list[dict[str, object]] = []
    ece = 0.0
    max_gap = 0.0
    total = float(len(local))
    for bin_index, bin_group in local.groupby("bin_index", sort=True):
        actual = float(bin_group["target"].mean())
        predicted = float(bin_group["model_probability"].mean())
        gap = abs(predicted - actual)
        weight = float(len(bin_group) / total)
        ece += weight * gap
        max_gap = max(max_gap, gap)
        bins.append(
            {
                "bin_index": int(bin_index) + 1,
                "rows": int(len(bin_group)),
                "mean_probability": round(predicted, 6),
                "actual_positive_rate": round(actual, 6),
                "abs_gap": round(gap, 6),
            }
        )
    return bins, round(ece, 6), round(max_gap, 6)


def subgroup_metrics(
    group: pd.DataFrame,
    segment_type: str,
    segment_value: str,
    overall_metrics: dict[str, float],
    n_bins: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    y_true = group["target"]
    y_pred = group["model_prediction"]
    y_prob = group["model_probability"]

    positives = int(y_true.sum())
    negatives = int((1 - y_true).sum())
    false_positives = int(((y_pred == 1) & (y_true == 0)).sum())
    false_negatives = int(((y_pred == 0) & (y_true == 1)).sum())
    tpr = float(recall_score(y_true, y_pred, zero_division=0))
    fpr = float(false_positives / negatives) if negatives else 0.0
    fnr = float(false_negatives / positives) if positives else 0.0
    ap = safe_average_precision(y_true, y_prob)
    auc = safe_roc_auc(y_true, y_prob)
    bins, ece, max_gap = build_calibration_bins(group, n_bins)

    row = {
        "segment_type": segment_type,
        "segment_value": segment_value,
        "rows": int(len(group)),
        "positive_rows": positives,
        "actual_positive_rate": round(float(y_true.mean()), 6),
        "predicted_positive_rate": round(float(y_pred.mean()), 6),
        "mean_probability": round(float(y_prob.mean()), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(tpr, 6),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "false_positive_rate": round(fpr, 6),
        "false_negative_rate": round(fnr, 6),
        "average_precision": round(ap, 6),
        "roc_auc": round(auc, 6) if auc is not None else "",
        "brier_score": round(float(brier_score_loss(y_true, y_prob)), 6),
        "calibration_ece": ece,
        "max_calibration_gap": max_gap,
        "recall_gap_vs_overall": round(tpr - overall_metrics["recall"], 6),
        "fpr_gap_vs_overall": round(fpr - overall_metrics["false_positive_rate"], 6),
        "ece_gap_vs_overall": round(ece - overall_metrics["calibration_ece"], 6),
        "mean_probability_gap_vs_actual": round(float(y_prob.mean()) - float(y_true.mean()), 6),
    }

    calibration_rows = [
        {
            "segment_type": segment_type,
            "segment_value": segment_value,
            **bin_row,
        }
        for bin_row in bins
    ]
    return row, calibration_rows


def build_report_tables(df: pd.DataFrame, min_group_rows: int, n_bins: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    overall_bins, overall_ece, overall_max_gap = build_calibration_bins(df, n_bins)
    overall_metrics = {
        "recall": float(recall_score(df["target"], df["model_prediction"], zero_division=0)),
        "false_positive_rate": float((((df["model_prediction"] == 1) & (df["target"] == 0)).sum()) / max(int((df["target"] == 0).sum()), 1)),
        "calibration_ece": overall_ece,
    }
    segment_rows: list[dict[str, object]] = [
        {
            "segment_type": "overall",
            "segment_value": "overall",
            "rows": int(len(df)),
            "positive_rows": int(df["target"].sum()),
            "actual_positive_rate": round(float(df["target"].mean()), 6),
            "predicted_positive_rate": round(float(df["model_prediction"].mean()), 6),
            "mean_probability": round(float(df["model_probability"].mean()), 6),
            "precision": round(float(precision_score(df["target"], df["model_prediction"], zero_division=0)), 6),
            "recall": round(overall_metrics["recall"], 6),
            "f1": round(float(f1_score(df["target"], df["model_prediction"], zero_division=0)), 6),
            "false_positive_rate": round(overall_metrics["false_positive_rate"], 6),
            "false_negative_rate": round(float((((df["model_prediction"] == 0) & (df["target"] == 1)).sum()) / max(int(df["target"].sum()), 1)), 6),
            "average_precision": round(safe_average_precision(df["target"], df["model_probability"]), 6),
            "roc_auc": round(float(roc_auc_score(df["target"], df["model_probability"])), 6),
            "brier_score": round(float(brier_score_loss(df["target"], df["model_probability"])), 6),
            "calibration_ece": overall_ece,
            "max_calibration_gap": overall_max_gap,
            "recall_gap_vs_overall": 0.0,
            "fpr_gap_vs_overall": 0.0,
            "ece_gap_vs_overall": 0.0,
            "mean_probability_gap_vs_actual": round(float(df["model_probability"].mean()) - float(df["target"].mean()), 6),
        }
    ]
    calibration_rows: list[dict[str, object]] = [
        {"segment_type": "overall", "segment_value": "overall", **row}
        for row in overall_bins
    ]

    segment_specs = {
        "borough": df["borough"].fillna("UNKNOWN").astype(str),
        "management_program": df["management_program"].fillna("UNKNOWN").astype(str),
        "cre_bucket": build_cre_bucket(df["cre_vulnerability_index"], df["cre_coverage_flag"]),
    }

    for segment_type, values in segment_specs.items():
        local = df.copy()
        local["_segment"] = values
        for segment_value, group in local.groupby("_segment", sort=False):
            if len(group) < min_group_rows:
                continue
            row, cal_rows = subgroup_metrics(group, segment_type, str(segment_value), overall_metrics, n_bins)
            segment_rows.append(row)
            calibration_rows.extend(cal_rows)
    return segment_rows, calibration_rows


def write_report(path: Path, segment_rows: list[dict[str, object]]) -> None:
    df = pd.DataFrame(segment_rows)
    overall = df[(df["segment_type"] == "overall")].iloc[0]
    borough = df[df["segment_type"] == "borough"].sort_values("recall")
    management = df[df["segment_type"] == "management_program"].sort_values("calibration_ece", ascending=False)
    cre = df[df["segment_type"] == "cre_bucket"].sort_values("calibration_ece", ascending=False)

    lines = [
        "# Subgroup Fairness and Calibration",
        "",
        "This report evaluates held-out subgroup behavior for thresholded performance and probability calibration.",
        "",
        "## Overall held-out benchmark",
        f"- Rows: `{int(overall['rows'])}`",
        f"- Actual positive rate: `{overall['actual_positive_rate']}`",
        f"- Precision: `{overall['precision']}` | Recall: `{overall['recall']}` | F1: `{overall['f1']}`",
        f"- Brier score: `{overall['brier_score']}` | ECE: `{overall['calibration_ece']}` | Max gap: `{overall['max_calibration_gap']}`",
        "",
    ]

    if not borough.empty:
        lowest = borough.iloc[0]
        highest = borough.iloc[-1]
        lines.extend(
            [
                "## Borough parity",
                f"- Lowest borough recall: `{lowest['segment_value']}` with recall `{lowest['recall']}` and ECE `{lowest['calibration_ece']}`",
                f"- Highest borough recall: `{highest['segment_value']}` with recall `{highest['recall']}` and ECE `{highest['calibration_ece']}`",
                f"- Borough recall spread: `{round(float(highest['recall']) - float(lowest['recall']), 6)}`",
                "",
            ]
        )

    if not management.empty:
        worst_mgmt = management.iloc[0]
        best_mgmt = management.sort_values("calibration_ece").iloc[0]
        lines.extend(
            [
                "## Management-program calibration",
                f"- Worst management-program ECE: `{worst_mgmt['segment_value']}` -> `{worst_mgmt['calibration_ece']}`",
                f"- Best management-program ECE: `{best_mgmt['segment_value']}` -> `{best_mgmt['calibration_ece']}`",
                "",
            ]
        )

    if not cre.empty:
        worst_cre = cre.iloc[0]
        high_cre = cre[cre["segment_value"] == "high"]
        low_cre = cre[cre["segment_value"] == "low"]
        lines.extend(["## Vulnerability-bucket behavior"])
        if not high_cre.empty and not low_cre.empty:
            high_row = high_cre.iloc[0]
            low_row = low_cre.iloc[0]
            lines.extend(
                [
                    f"- High-vulnerability bucket recall: `{high_row['recall']}` | ECE `{high_row['calibration_ece']}` | mean prob gap `{high_row['mean_probability_gap_vs_actual']}`",
                    f"- Low-vulnerability bucket recall: `{low_row['recall']}` | ECE `{low_row['calibration_ece']}` | mean prob gap `{low_row['mean_probability_gap_vs_actual']}`",
                ]
            )
        lines.extend(
            [
                f"- Worst CRE-bucket ECE: `{worst_cre['segment_value']}` -> `{worst_cre['calibration_ece']}`",
                "",
                "## Interpretation",
                "- This report is not claiming legal fairness; it is checking whether subgroup performance and calibration are materially uneven across operationally important strata.",
                "- If a subgroup shows lower recall and worse ECE at the same time, that is the first place to revisit threshold policy, features, or retraining cadence.",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    scored = load_scored_splits(Path(args.input), FAIRNESS_COLUMNS, {"test"})
    if scored.empty:
        raise ValueError("No test rows were found in the scored CSV.")

    for column in ["target", "model_prediction", "model_probability", "cre_vulnerability_index", "cre_coverage_flag"]:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0)

    segments, calibration = build_report_tables(scored, args.min_group_rows, args.n_bins)

    write_csv(Path(args.segments_output), segments)
    write_csv(Path(args.calibration_output), calibration)
    write_report(Path(args.report_output), segments)

    print(f"wrote subgroup fairness segments to {args.segments_output}", flush=True)
    print(f"wrote subgroup calibration bins to {args.calibration_output}", flush=True)
    print(f"wrote subgroup fairness report to {args.report_output}", flush=True)


if __name__ == "__main__":
    main()
