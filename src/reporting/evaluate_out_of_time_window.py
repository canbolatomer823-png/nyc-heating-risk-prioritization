from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.logistic_regression_model import (
    LOGISTIC_PREPARED_COLUMNS,
    apply_calibration,
    compute_daily_ranking_metrics,
    compute_metrics,
    summarize_ranking_metrics,
)
from modeling.risk_features import MODEL_INPUT_COLUMNS, load_prepared_modeling_table
from project_paths import (
    FINAL_MODEL_BUNDLE_PATH,
    OOT_MODELING_TABLE_PATH,
    OOT_SCORED_CSV_PATH,
    OOT_VALIDATION_RANKING_METRICS_PATH,
    OOT_VALIDATION_REPORT_PATH,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the frozen final logistic bundle on a non-overlapping out-of-time window."
    )
    parser.add_argument(
        "--input",
        default=str(OOT_MODELING_TABLE_PATH),
        help="Prepared modeling table for the out-of-time window.",
    )
    parser.add_argument(
        "--bundle",
        default=str(FINAL_MODEL_BUNDLE_PATH),
        help="Path to the trained logistic regression bundle.",
    )
    parser.add_argument(
        "--scored-output",
        default=str(OOT_SCORED_CSV_PATH),
        help="CSV path for scored out-of-time rows.",
    )
    parser.add_argument(
        "--ranking-output",
        default=str(OOT_VALIDATION_RANKING_METRICS_PATH),
        help="CSV path for daily ranking metrics on the out-of-time window.",
    )
    parser.add_argument(
        "--report-output",
        default=str(OOT_VALIDATION_REPORT_PATH),
        help="Markdown summary output path.",
    )
    return parser.parse_args()


def as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def format_delta(current: object, reference: object) -> str:
    current_float = as_float(current)
    reference_float = as_float(reference)
    if current_float is None or reference_float is None:
        return "n/a"
    delta = current_float - reference_float
    return f"{delta:+.4f}"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    bundle_path = Path(args.bundle)
    scored_output_path = Path(args.scored_output)
    ranking_output_path = Path(args.ranking_output)
    report_output_path = Path(args.report_output)

    bundle = joblib.load(bundle_path)
    model = bundle["model"]
    calibrator = bundle.get("calibrator")
    metadata = bundle.get("metadata", {})
    threshold = float(metadata.get("threshold", 0.5))

    oot_df = load_prepared_modeling_table(input_path, columns=LOGISTIC_PREPARED_COLUMNS)
    if oot_df.empty:
        raise ValueError(f"No rows were loaded from {input_path}")

    raw_probabilities = model.predict_proba(oot_df[MODEL_INPUT_COLUMNS])[:, 1]
    probabilities = apply_calibration(calibrator, raw_probabilities)

    scored = oot_df.copy()
    scored["raw_model_probability"] = raw_probabilities
    scored["model_probability"] = probabilities
    scored["model_threshold"] = threshold
    scored["model_prediction"] = (scored["model_probability"] >= threshold).astype(int)
    scored["data_split"] = "out_of_time"

    scored_output_path.parent.mkdir(parents=True, exist_ok=True)
    scored_to_write = scored.copy()
    scored_to_write["calendar_date"] = scored_to_write["calendar_date"].dt.strftime("%Y-%m-%d")
    scored_to_write.to_csv(scored_output_path, index=False)

    metrics = compute_metrics(scored["target"], scored["model_probability"], threshold)
    ranking_metrics = compute_daily_ranking_metrics(scored)
    ranking_output_path.parent.mkdir(parents=True, exist_ok=True)
    ranking_metrics.to_csv(ranking_output_path, index=False)
    ranking_summary = summarize_ranking_metrics(ranking_metrics)

    date_min = scored["calendar_date"].min()
    date_max = scored["calendar_date"].max()
    in_window_metrics = metadata.get("metrics", {}).get("test", {})
    in_window_ranking = metadata.get("ranking_metrics", {})

    lines = [
        "# Out-of-Time Validation",
        "",
        "This report evaluates the frozen calibrated logistic bundle trained on the final heat-season window",
        "against a non-overlapping future slice without any retraining.",
        "",
        f"- Training window (full project): {metadata.get('date_ranges', {}).get('train', ['n/a', 'n/a'])[0]} -> {metadata.get('date_ranges', {}).get('test', ['n/a', 'n/a'])[1]}",
        f"- Out-of-time evaluation window: {str(date_min)[:10]} -> {str(date_max)[:10]}",
        f"- Threshold reused from final bundle: {threshold}",
        f"- Rows scored: {len(scored)}",
        f"- Distinct buildings: {scored['building_id'].nunique()}",
        f"- Distinct days: {scored['calendar_date'].nunique()}",
        "",
        "## Out-of-Time Classification Metrics",
        f"- Actual positive rate: {metrics['actual_positive_rate']}",
        f"- Mean probability: {metrics['mean_probability']}",
        f"- Predicted positive rate: {metrics['predicted_positive_rate']}",
        f"- Precision: {metrics['precision']}",
        f"- Recall: {metrics['recall']}",
        f"- F1: {metrics['f1']}",
        f"- Average precision: {metrics['average_precision']}",
        f"- Brier score: {metrics['brier_score']}",
        f"- ROC AUC: {metrics['roc_auc']}",
        "",
        "## Delta vs Final In-Window Held-Out Test",
        f"- Precision delta: {format_delta(metrics.get('precision'), in_window_metrics.get('precision'))}",
        f"- Recall delta: {format_delta(metrics.get('recall'), in_window_metrics.get('recall'))}",
        f"- F1 delta: {format_delta(metrics.get('f1'), in_window_metrics.get('f1'))}",
        f"- Average precision delta: {format_delta(metrics.get('average_precision'), in_window_metrics.get('average_precision'))}",
        f"- ROC AUC delta: {format_delta(metrics.get('roc_auc'), in_window_metrics.get('roc_auc'))}",
        "",
        "## Out-of-Time Ranking Summary",
    ]

    for k in sorted(ranking_summary):
        summary = ranking_summary[k]
        reference = in_window_ranking.get(k) or in_window_ranking.get(str(k), {})
        lines.extend(
            [
                f"### Top {k}",
                f"- Mean Precision@{k}: {summary['mean_precision_at_k']}",
                f"- Mean Recall@{k}: {summary['mean_recall_at_k']}",
                f"- Mean Lift@{k}: {summary['mean_lift_at_k']}",
                f"- Latest day: {summary['latest_date']}",
                f"- Latest Precision@{k}: {summary['latest_precision_at_k']}",
                f"- Latest hits@{k}: {summary['latest_hits_at_k']}",
                f"- Delta vs in-window mean Precision@{k}: {format_delta(summary['mean_precision_at_k'], reference.get('mean_precision_at_k'))}",
                f"- Delta vs in-window mean Lift@{k}: {format_delta(summary['mean_lift_at_k'], reference.get('mean_lift_at_k'))}",
                "",
            ]
        )

    lines.extend(
        [
            "## Artifact Outputs",
            f"- Scored rows: {scored_output_path}",
            f"- Ranking metrics: {ranking_output_path}",
            "",
            "## Metadata Snapshot",
            "```json",
            json.dumps(
                {
                    "bundle_path": str(bundle_path),
                    "input_path": str(input_path),
                    "threshold": threshold,
                    "in_window_test_metrics": in_window_metrics,
                    "out_of_time_metrics": metrics,
                },
                indent=2,
            ),
            "```",
            "",
        ]
    )

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote out-of-time report to {report_output_path}")


if __name__ == "__main__":
    main()
