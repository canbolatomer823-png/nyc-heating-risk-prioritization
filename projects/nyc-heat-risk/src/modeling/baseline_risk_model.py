from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_DENSE_PANEL_PATH, FINAL_REPORTS_DIR

FINAL_BASELINE_SCORED_PATH = FINAL_REPORTS_DIR / "baseline_building_day_scored.csv"
FINAL_BASELINE_METRICS_PATH = FINAL_REPORTS_DIR / "baseline_model_metrics.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_int(value: str) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def safe_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def score_row(row: dict[str, str]) -> float:
    complaint_count = safe_int(row.get("complaint_count", "0"))
    unique_request_count = safe_int(row.get("unique_request_count", "0"))
    rolling_3d = safe_int(row.get("rolling_3d_complaints", "0"))
    rolling_7d = safe_int(row.get("rolling_7d_complaints", "0"))
    lag_1 = safe_int(row.get("lag_1_complaints", "0"))
    complaint_day_count_prior = safe_int(row.get("complaint_day_count_prior", "0"))
    cumulative_prior = safe_int(row.get("cumulative_complaints_prior", "0"))
    prior_max = safe_int(row.get("prior_max_daily_complaints", "0"))
    days_since_last = safe_int(row.get("days_since_last_complaint", "-1"))
    open_violations = safe_int(row.get("open_linked_violation_count", "0"))
    units = safe_int(row.get("unit_count_proxy", "0"))
    registration_active = safe_int(row.get("registration_active_flag", "0"))
    heat_sensor_active = safe_int(row.get("heat_sensor_active_flag", "0"))
    heating_degree = safe_float(row.get("weather_heating_degree_c", "0"))
    freezing_flag = safe_int(row.get("weather_freezing_any_flag", "0"))
    cold_shock_flag = safe_int(row.get("weather_cold_shock_flag", "0"))
    weather_temp_drop = safe_float(row.get("weather_temp_drop_c", "0"))

    risk_score = 0.0
    risk_score += min(complaint_count / 2.0, 1.0) * 0.22
    risk_score += min(unique_request_count / 2.0, 1.0) * 0.05
    risk_score += min(rolling_3d / 4.0, 1.0) * 0.18
    risk_score += min(rolling_7d / 7.0, 1.0) * 0.14
    risk_score += min(lag_1 / 2.0, 1.0) * 0.08
    risk_score += min(cumulative_prior / 10.0, 1.0) * 0.08
    risk_score += min(complaint_day_count_prior / 5.0, 1.0) * 0.04
    risk_score += min(prior_max / 3.0, 1.0) * 0.04
    risk_score += min(open_violations / 50.0, 1.0) * 0.07
    risk_score += (1 if heat_sensor_active >= 1 else 0) * 0.05
    risk_score += (1 if 0 <= days_since_last <= 2 else 0) * 0.03
    risk_score += min(heating_degree / 10.0, 1.0) * 0.04
    risk_score += (1 if freezing_flag >= 1 else 0) * 0.04
    risk_score += (1 if cold_shock_flag >= 1 else 0) * 0.03
    risk_score += min(weather_temp_drop / 5.0, 1.0) * 0.03
    risk_score += (1 if units >= 50 else 0) * 0.01
    risk_score += min(registration_active, 1) * 0.01

    return round(risk_score, 4)


def evaluate(rows: list[dict[str, str]], threshold: float) -> dict[str, float | int]:
    total = len(rows)
    tp = fp = tn = fn = 0

    scored_rows: list[dict[str, str | float | int]] = []
    for row in rows:
        actual = safe_int(row.get("next_day_complaint_count", "0"))
        actual_flag = 1 if actual >= 1 else 0
        risk_score = score_row(row)
        predicted_flag = 1 if risk_score >= threshold else 0

        if predicted_flag == 1 and actual_flag == 1:
            tp += 1
        elif predicted_flag == 1 and actual_flag == 0:
            fp += 1
        elif predicted_flag == 0 and actual_flag == 0:
            tn += 1
        else:
            fn += 1

        row = dict(row)
        row["baseline_risk_score"] = risk_score
        row["baseline_threshold"] = round(threshold, 4)
        row["baseline_predicted_next_day_flag"] = predicted_flag
        row["actual_next_day_count"] = actual
        row["actual_next_day_flag"] = actual_flag
        scored_rows.append(row)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / total if total else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    actual_positive_rate = (tp + fn) / total if total else 0.0
    predicted_positive_rate = (tp + fp) / total if total else 0.0

    return {
        "row_count": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "actual_positive_rate": round(actual_positive_rate, 4),
        "predicted_positive_rate": round(predicted_positive_rate, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "scored_rows": scored_rows,
    }


def filter_labeled_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if safe_int(row.get("next_day_label_available", "0")) == 1]


def split_rows_by_date(rows: list[dict[str, str]], test_ratio: float = 0.2) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    unique_dates = sorted({(row.get("calendar_date") or "").strip() for row in rows if (row.get("calendar_date") or "").strip()})
    if len(unique_dates) < 2:
        return rows, rows

    split_index = int(len(unique_dates) * (1 - test_ratio))
    split_index = min(max(split_index, 1), len(unique_dates) - 1)
    train_dates = set(unique_dates[:split_index])
    test_dates = set(unique_dates[split_index:])

    train_rows = [row for row in rows if row.get("calendar_date") in train_dates]
    test_rows = [row for row in rows if row.get("calendar_date") in test_dates]
    return train_rows, test_rows


def tune_threshold(rows: list[dict[str, str]]) -> float:
    best_threshold = 0.35
    best_metrics: tuple[float, float, float] | None = None

    for raw_threshold in range(20, 81, 5):
        threshold = raw_threshold / 100
        metrics = evaluate(rows, threshold)
        score = (metrics["f1"], metrics["recall"], -threshold)
        if best_metrics is None or score > best_metrics:
            best_threshold = threshold
            best_metrics = score

    return best_threshold


def write_scored_csv(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_metrics(
    path: Path,
    train_metrics: dict[str, float | int],
    test_metrics: dict[str, float | int],
    threshold: float,
    train_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
) -> None:
    train_dates = sorted({row.get("calendar_date", "") for row in train_rows if row.get("calendar_date")})
    test_dates = sorted({row.get("calendar_date", "") for row in test_rows if row.get("calendar_date")})
    lines = [
        "# Baseline Model Metrics",
        "",
        "## Setup",
        f"- Decision threshold: {round(threshold, 4)}",
        f"- Train date range: {train_dates[0] if train_dates else 'n/a'} -> {train_dates[-1] if train_dates else 'n/a'}",
        f"- Test date range: {test_dates[0] if test_dates else 'n/a'} -> {test_dates[-1] if test_dates else 'n/a'}",
        "",
        "## Train Metrics",
        f"- Rows: {train_metrics['row_count']}",
        f"- Accuracy: {train_metrics['accuracy']}",
        f"- Precision: {train_metrics['precision']}",
        f"- Recall: {train_metrics['recall']}",
        f"- F1: {train_metrics['f1']}",
        f"- Actual positive rate: {train_metrics['actual_positive_rate']}",
        f"- Predicted positive rate: {train_metrics['predicted_positive_rate']}",
        "",
        "## Test Metrics",
        f"- Rows: {test_metrics['row_count']}",
        f"- Accuracy: {test_metrics['accuracy']}",
        f"- Precision: {test_metrics['precision']}",
        f"- Recall: {test_metrics['recall']}",
        f"- F1: {test_metrics['f1']}",
        f"- Actual positive rate: {test_metrics['actual_positive_rate']}",
        f"- Predicted positive rate: {test_metrics['predicted_positive_rate']}",
        f"- TP: {test_metrics['tp']}",
        f"- FP: {test_metrics['fp']}",
        f"- TN: {test_metrics['tn']}",
        f"- FN: {test_metrics['fn']}",
        "",
        "This is a rule-based baseline, not the final statistical model.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a first baseline risk model on the dense building-day panel.")
    parser.add_argument(
        "--input",
        default=str(FINAL_DENSE_PANEL_PATH),
        help="Dense panel CSV path.",
    )
    parser.add_argument(
        "--scored-output",
        default=str(FINAL_BASELINE_SCORED_PATH),
        help="Scored CSV output path.",
    )
    parser.add_argument(
        "--metrics-output",
        default=str(FINAL_BASELINE_METRICS_PATH),
        help="Metrics markdown output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = filter_labeled_rows(read_csv(Path(args.input)))
    train_rows, test_rows = split_rows_by_date(rows)
    threshold = tune_threshold(train_rows)
    train_metrics = evaluate(train_rows, threshold)
    test_metrics = evaluate(test_rows, threshold)

    scored_rows: list[dict[str, str | float | int]] = []
    for split_name, split_rows in (("train", train_rows), ("test", test_rows)):
        split_metrics = evaluate(split_rows, threshold)
        for row in split_metrics["scored_rows"]:
            row = dict(row)
            row["data_split"] = split_name
            scored_rows.append(row)

    write_scored_csv(Path(args.scored_output), scored_rows)
    train_metrics.pop("scored_rows")
    test_metrics.pop("scored_rows")
    write_metrics(Path(args.metrics_output), train_metrics, test_metrics, threshold, train_rows, test_rows)
    print(f"wrote scored output to {args.scored_output}", flush=True)
    print(f"wrote metrics to {args.metrics_output}", flush=True)


if __name__ == "__main__":
    main()
