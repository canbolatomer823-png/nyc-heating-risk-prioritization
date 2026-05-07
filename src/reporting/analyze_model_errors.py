from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_ERROR_ANALYSIS_REPORT_PATH,
    FINAL_ERROR_ANALYSIS_SEGMENTS_PATH,
    FINAL_ERROR_ANALYSIS_TOP_ERRORS_PATH,
    FINAL_SCORED_CSV_PATH,
)
from reporting.evaluation_utils import classification_metrics, load_scored_splits, write_csv


ERROR_ANALYSIS_COLUMNS = [
    "calendar_date",
    "building_id",
    "incident_address",
    "borough",
    "target",
    "model_prediction",
    "model_probability",
    "cre_vulnerability_index",
    "cumulative_complaints_prior",
    "rolling_7d_complaints",
    "open_linked_violation_count",
    "complaint_count",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze held-out model errors by segment.")
    parser.add_argument("--input", default=str(FINAL_SCORED_CSV_PATH), help="Scored CSV with held-out predictions.")
    parser.add_argument(
        "--segments-output",
        default=str(FINAL_ERROR_ANALYSIS_SEGMENTS_PATH),
        help="CSV output path for segmented error metrics.",
    )
    parser.add_argument(
        "--top-errors-output",
        default=str(FINAL_ERROR_ANALYSIS_TOP_ERRORS_PATH),
        help="CSV output path for top false positives and false negatives.",
    )
    parser.add_argument(
        "--report-output",
        default=str(FINAL_ERROR_ANALYSIS_REPORT_PATH),
        help="Markdown report output path.",
    )
    return parser.parse_args()


def build_cre_bucket(series: pd.Series) -> pd.Series:
    valid = series.fillna(0)
    try:
        buckets = pd.qcut(valid.rank(method="first"), q=3, labels=["low", "mid", "high"])
        return buckets.astype(str)
    except ValueError:
        return pd.Series(["mid"] * len(series), index=series.index, dtype="object")


def build_history_bucket(series: pd.Series) -> pd.Series:
    return pd.cut(
        series.fillna(0),
        bins=[-1, 0, 4, 14, float("inf")],
        labels=["0", "1-4", "5-14", "15+"],
    ).astype(str)


def build_violation_bucket(series: pd.Series) -> pd.Series:
    return pd.cut(
        series.fillna(0),
        bins=[-1, 0, 1, 4, float("inf")],
        labels=["0", "1", "2-4", "5+"],
    ).astype(str)


def segment_rows(df: pd.DataFrame, segment_type: str, segment_value: str, group: pd.DataFrame) -> dict[str, object]:
    metrics = classification_metrics(group["target"], group["model_prediction"], group["model_probability"])
    false_positives = int(((group["model_prediction"] == 1) & (group["target"] == 0)).sum())
    false_negatives = int(((group["model_prediction"] == 0) & (group["target"] == 1)).sum())
    return {
        "segment_type": segment_type,
        "segment_value": segment_value,
        "rows": int(len(group)),
        "actual_positive_rate": round(metrics["actual_positive_rate"], 6),
        "predicted_positive_rate": round(metrics["predicted_positive_rate"], 6),
        "precision": round(metrics["precision"], 6),
        "recall": round(metrics["recall"], 6),
        "f1": round(metrics["f1"], 6),
        "mean_probability": round(metrics["mean_probability"], 6),
        "average_precision": round(metrics["average_precision"], 6),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def build_segment_table(df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    segment_specs = {
        "borough": df["borough"].fillna("UNKNOWN").astype(str),
        "month": pd.to_datetime(df["calendar_date"]).dt.strftime("%Y-%m"),
        "cre_bucket": build_cre_bucket(df["cre_vulnerability_index"]),
        "history_bucket": build_history_bucket(df["cumulative_complaints_prior"]),
        "violation_bucket": build_violation_bucket(df["open_linked_violation_count"]),
    }

    for segment_type, segment_values in segment_specs.items():
        local = df.copy()
        local["_segment"] = segment_values
        for segment_value, group in local.groupby("_segment"):
            rows.append(segment_rows(local, segment_type, str(segment_value), group))
    return rows


def top_errors(df: pd.DataFrame, limit: int = 25) -> list[dict[str, object]]:
    false_positives = (
        df[(df["model_prediction"] == 1) & (df["target"] == 0)]
        .sort_values("model_probability", ascending=False)
        .head(limit)
        .copy()
    )
    false_positives["error_type"] = "false_positive"

    false_negatives = (
        df[(df["model_prediction"] == 0) & (df["target"] == 1)]
        .sort_values("model_probability", ascending=False)
        .head(limit)
        .copy()
    )
    false_negatives["error_type"] = "false_negative"

    combined = pd.concat([false_positives, false_negatives], ignore_index=True)
    columns = [
        "error_type",
        "calendar_date",
        "building_id",
        "borough",
        "incident_address",
        "model_probability",
        "target",
        "model_prediction",
        "cre_vulnerability_index",
        "cumulative_complaints_prior",
        "rolling_7d_complaints",
        "open_linked_violation_count",
        "complaint_count",
    ]
    return combined[columns].to_dict(orient="records")


def write_report(path: Path, segment_table: list[dict[str, object]]) -> None:
    df = pd.DataFrame(segment_table)
    lines = [
        "# Error Analysis",
        "",
        "This report slices held-out test errors by borough, month, vulnerability bucket, complaint-history bucket, and violation bucket.",
        "",
    ]

    if not df.empty:
        borough = df[df["segment_type"] == "borough"].sort_values("recall")
        cre = df[df["segment_type"] == "cre_bucket"].sort_values("f1")
        history = df[df["segment_type"] == "history_bucket"].sort_values("false_negatives", ascending=False)
        violations = df[df["segment_type"] == "violation_bucket"].sort_values("precision")

        lines.extend(
            [
                "## Key findings",
                f"- Lowest borough recall: `{borough.iloc[0]['segment_value']}` with recall `{borough.iloc[0]['recall']}`",
                f"- Highest borough recall: `{borough.iloc[-1]['segment_value']}` with recall `{borough.iloc[-1]['recall']}`",
                f"- Lowest F1 CRE bucket: `{cre.iloc[0]['segment_value']}` with F1 `{cre.iloc[0]['f1']}`",
                f"- Highest false-negative history bucket: `{history.iloc[0]['segment_value']}` with `{int(history.iloc[0]['false_negatives'])}` misses",
                f"- Lowest precision violation bucket: `{violations.iloc[0]['segment_value']}` with precision `{violations.iloc[0]['precision']}`",
                "",
                "## Interpretation",
                "- This table is designed to answer where the model struggles, not just what the global metric is.",
                "- If the weakest segments align with high-vulnerability or chronic-history buckets, those are the first places to improve with feature work or threshold policy changes.",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    scored = load_scored_splits(Path(args.input), ERROR_ANALYSIS_COLUMNS, {"test"})
    if scored.empty:
        raise ValueError("No test rows were found in the scored CSV.")

    numeric_columns = [
        "target",
        "model_prediction",
        "model_probability",
        "cre_vulnerability_index",
        "cumulative_complaints_prior",
        "rolling_7d_complaints",
        "open_linked_violation_count",
        "complaint_count",
    ]
    for column in numeric_columns:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0)

    segments = build_segment_table(scored)
    top_error_rows = top_errors(scored)

    write_csv(Path(args.segments_output), segments)
    write_csv(Path(args.top_errors_output), top_error_rows)
    write_report(Path(args.report_output), segments)

    print(f"wrote error segments to {args.segments_output}", flush=True)
    print(f"wrote top errors to {args.top_errors_output}", flush=True)
    print(f"wrote report to {args.report_output}", flush=True)


if __name__ == "__main__":
    main()
