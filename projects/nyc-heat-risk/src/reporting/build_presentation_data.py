from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_WINDOW_ROOT, OOT_VALIDATION_REPORT_PATH, PROJECT_ROOT


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: str | float | int | None) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def safe_int(value: str | float | int | None) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def require_match(match: re.Match[str] | None, label: str) -> re.Match[str]:
    if match is None:
        raise ValueError(f"Could not parse required value for: {label}")
    return match


def month_start(date_text: str) -> str:
    date_obj = datetime.strptime(date_text[:10], "%Y-%m-%d")
    return date_obj.strftime("%Y-%m-01")


def count_data_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def parse_profile_cre_coverage(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    dense_match = require_match(re.search(r"## Dense panel\s+- Row count: ([0-9]+)", text, flags=re.S), "dense row count")
    cre_match = require_match(re.search(r"- CRE-covered row count: ([0-9]+)", text), "CRE-covered row count")
    dense_rows = int(dense_match.group(1))
    cre_rows = int(cre_match.group(1))
    return dense_rows, cre_rows


def parse_rolling_backtest(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    def extract(label: str) -> float:
        match = require_match(re.search(rf"{re.escape(label)}: `?([0-9.]+)`?", text), f"rolling metric {label}")
        return float(match.group(1))

    return {
        "mean_f1": extract("Mean F1"),
        "mean_roc_auc": extract("Mean ROC AUC"),
    }


def parse_section_metrics(path: Path, section_name: str) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    pattern = rf"## {re.escape(section_name)}\n(.*?)(?:\n## |\Z)"
    match = require_match(re.search(pattern, text, flags=re.S), f"section {section_name}")
    block = match.group(1)
    metrics: dict[str, float] = {}
    for line in block.splitlines():
        if not line.startswith("- "):
            continue
        body = line[2:]
        if ": " not in body:
            continue
        key, value = body.split(": ", 1)
        try:
            metrics[key.strip()] = float(value.strip())
        except ValueError:
            continue
    return metrics


def parse_markdown_bullet_section(text: str, heading: str) -> dict[str, str]:
    pattern = rf"## {re.escape(heading)}\n(.*?)(?:\n## |\Z)"
    match = require_match(re.search(pattern, text, flags=re.S), f"section {heading}")
    block = match.group(1)
    values: dict[str, str] = {}
    for line in block.splitlines():
        if not line.startswith("- "):
            continue
        body = line[2:]
        if ": " not in body:
            continue
        key, value = body.split(": ", 1)
        values[key.strip()] = value.strip()
    return values


def parse_seasonal_anova(path: Path) -> dict[str, float | str]:
    text = path.read_text(encoding="utf-8")

    def extract(pattern: str, label: str, cast=float):
        match = require_match(re.search(pattern, text), label)
        return cast(match.group(1))

    return {
        "monthly_complaints_f": extract(r"Daily total complaints: F=([0-9.]+), p=", "monthly complaints F", float),
        "monthly_complaints_eta_sq": extract(r"Daily total complaints: F=[0-9.]+, p=[^,]+, eta_sq=([0-9.]+)", "monthly complaints eta_sq", float),
        "monthly_positive_f": extract(r"Daily positive buildings: F=([0-9.]+), p=", "monthly positive F", float),
        "monthly_positive_eta_sq": extract(r"Daily positive buildings: F=[0-9.]+, p=[^,]+, eta_sq=([0-9.]+)", "monthly positive eta_sq", float),
        "peak_month": extract(r"Highest mean daily complaint month: ([^(]+)\s+\(", "peak month", str).strip(),
        "quiet_month": extract(r"Lowest mean daily complaint month: ([^(]+)\s+\(", "quiet month", str).strip(),
    }


def parse_out_of_time_validation(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    header = parse_markdown_bullet_section(text, "Out-of-Time Classification Metrics")
    delta = parse_markdown_bullet_section(text, "Delta vs Final In-Window Held-Out Test")
    lines = text.splitlines()

    meta: dict[str, str] = {}
    for line in lines:
        if not line.startswith("- "):
            continue
        body = line[2:]
        if ": " not in body:
            continue
        key, value = body.split(": ", 1)
        if key in {
            "Training window (full project)",
            "Out-of-time evaluation window",
            "Threshold reused from final bundle",
            "Rows scored",
            "Distinct buildings",
            "Distinct days",
        }:
            meta[key] = value.strip()

    ranking: dict[str, dict[str, float | str]] = {}
    for k in (10, 25, 50, 100):
        section = parse_markdown_bullet_section(text, f"Top {k}")
        ranking[str(k)] = {
            "mean_precision_at_k": safe_float(section.get(f"Mean Precision@{k}")),
            "mean_recall_at_k": safe_float(section.get(f"Mean Recall@{k}")),
            "mean_lift_at_k": safe_float(section.get(f"Mean Lift@{k}")),
            "latest_date": section.get("Latest day", ""),
            "latest_precision_at_k": safe_float(section.get(f"Latest Precision@{k}")),
            "latest_hits_at_k": safe_int(section.get(f"Latest hits@{k}")),
            "delta_mean_precision_at_k": safe_float(section.get(f"Delta vs in-window mean Precision@{k}")),
            "delta_mean_lift_at_k": safe_float(section.get(f"Delta vs in-window mean Lift@{k}")),
        }

    return {
        "window_label": meta.get("Out-of-time evaluation window", ""),
        "rows": safe_int(meta.get("Rows scored")),
        "distinct_buildings": safe_int(meta.get("Distinct buildings")),
        "distinct_days": safe_int(meta.get("Distinct days")),
        "threshold": safe_float(meta.get("Threshold reused from final bundle")),
        "metrics": {
            "actual_positive_rate": safe_float(header.get("Actual positive rate")),
            "mean_probability": safe_float(header.get("Mean probability")),
            "predicted_positive_rate": safe_float(header.get("Predicted positive rate")),
            "precision": safe_float(header.get("Precision")),
            "recall": safe_float(header.get("Recall")),
            "f1": safe_float(header.get("F1")),
            "average_precision": safe_float(header.get("Average precision")),
            "brier_score": safe_float(header.get("Brier score")),
            "roc_auc": safe_float(header.get("ROC AUC")),
        },
        "delta_vs_in_window": {
            "precision": safe_float(delta.get("Precision delta")),
            "recall": safe_float(delta.get("Recall delta")),
            "f1": safe_float(delta.get("F1 delta")),
            "average_precision": safe_float(delta.get("Average precision delta")),
            "roc_auc": safe_float(delta.get("ROC AUC delta")),
        },
        "ranking_metrics": ranking,
    }


def load_selected_effects(path: Path) -> list[dict[str, float | str]]:
    rows = read_csv_rows(path)
    wanted_terms = [
        ("gee_logistic", "cre_vulnerability_index", "CRE vulnerability (GEE)"),
        ("gee_logistic", "weather_heating_degree_scaled", "Heating degree (GEE)"),
        ("gee_logistic", "weather_temp_drop_c", "Temp drop (GEE)"),
        ("gee_logistic", "recent_complaint_flag", "Recent complaint (GEE)"),
        ("negative_binomial", "weather_temp_drop_c", "Temp drop (NB)"),
        ("negative_binomial", "log1p_current_complaint_count", "Current complaint count (NB)"),
    ]

    effects: list[dict[str, float | str]] = []
    for model, term, label in wanted_terms:
        row = next((item for item in rows if item.get("model") == model and item.get("term") == term), None)
        if row is None:
            raise ValueError(f"Missing coefficient row for {model}:{term}")
        effects.append({"term": label, "effect": round(safe_float(row.get("effect")), 4)})
    return effects


def parse_glmm_random_intercept_sd(path: Path) -> float:
    rows = read_csv_rows(path)
    row = next(
        (
            item
            for item in rows
            if item.get("model") == "binomial_glmm" and item.get("term") == "sd_building_random_intercept"
        ),
        None,
    )
    if row is None:
        raise ValueError("Missing GLMM random intercept SD row.")
    return round(safe_float(row.get("effect")), 4)


def load_coefficient_detail_rows(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path)


def require_coefficient_row(rows: list[dict[str, str]], model: str, term: str) -> dict[str, str]:
    row = next((item for item in rows if item.get("model") == model and item.get("term") == term), None)
    if row is None:
        raise ValueError(f"Missing coefficient detail for {model}:{term}")
    return row


def build_monthly_trend(
    complaints_path: Path,
    sparse_panel_path: Path,
    weather_path: Path,
) -> list[dict[str, float | int | str]]:
    complaint_rows = read_csv_rows(complaints_path)
    sparse_rows = read_csv_rows(sparse_panel_path)
    weather_rows = read_csv_rows(weather_path)

    complaint_counts: Counter[str] = Counter()
    positive_buildings_by_month: dict[str, set[str]] = defaultdict(set)
    for row in complaint_rows:
        date_text = (row.get("received_date") or "")[:10]
        if not date_text:
            continue
        complaint_counts[month_start(date_text)] += 1

    for row in sparse_rows:
        date_text = (row.get("complaint_date") or "")[:10]
        building_id = (row.get("building_id") or "").strip()
        if date_text and building_id:
            positive_buildings_by_month[month_start(date_text)].add(building_id)

    weather_accumulator: dict[str, dict[str, float]] = defaultdict(lambda: {"avg_temp_c": 0.0, "heating_degree_c": 0.0, "days": 0.0})
    for row in weather_rows:
        date_text = (row.get("date") or "")[:10]
        if not date_text:
            continue
        bucket = weather_accumulator[month_start(date_text)]
        bucket["avg_temp_c"] += safe_float(row.get("weather_avg_temp_c"))
        bucket["heating_degree_c"] += safe_float(row.get("weather_heating_degree_c"))
        bucket["days"] += 1.0

    month_keys = sorted(set(complaint_counts) | set(positive_buildings_by_month) | set(weather_accumulator))
    trend: list[dict[str, float | int | str]] = []
    for key in month_keys:
        weather = weather_accumulator.get(key, {"avg_temp_c": 0.0, "heating_degree_c": 0.0, "days": 0.0})
        day_count = max(weather["days"], 1.0)
        trend.append(
            {
                "date": key,
                "complaint_days": complaint_counts.get(key, 0),
                "avg_temp_c": round(weather["avg_temp_c"] / day_count, 4),
                "heating_degree_c": round(weather["heating_degree_c"] / day_count, 4),
                "positive_buildings": len(positive_buildings_by_month.get(key, set())),
            }
        )
    return trend


def build_borough_positive(sparse_panel_path: Path) -> list[dict[str, int | str]]:
    sparse_rows = read_csv_rows(sparse_panel_path)
    counts: Counter[str] = Counter()
    buildings: dict[str, set[str]] = defaultdict(set)
    for row in sparse_rows:
        borough = (row.get("borough") or "UNKNOWN").strip() or "UNKNOWN"
        counts[borough] += 1
        building_id = (row.get("building_id") or "").strip()
        if building_id:
            buildings[borough].add(building_id)
    return [
        {
            "borough": borough,
            "positive_rows": count,
            "panel_rows": len(buildings.get(borough, set())),
        }
        for borough, count in counts.most_common()
    ]


def build_priority_outputs(priority_path: Path) -> tuple[list[dict[str, int | float | str]], list[dict[str, int | str]], dict[str, float | int]]:
    rows = read_csv_rows(priority_path)
    priority_top10: list[dict[str, int | float | str]] = []
    borough_mix = Counter((row.get("borough") or "UNKNOWN").strip() for row in rows)

    avg_probability = 0.0
    avg_equity_score = 0.0
    avg_open_violations = 0.0
    if rows:
        avg_probability = sum(safe_float(row.get("model_probability")) for row in rows) / len(rows)
        avg_equity_score = sum(safe_float(row.get("equity_weighted_priority_score")) for row in rows) / len(rows)
        avg_open_violations = sum(safe_float(row.get("open_linked_violation_count")) for row in rows) / len(rows)

    for row in rows[:10]:
        priority_top10.append(
            {
                "rank": safe_int(row.get("inspection_priority_rank")),
                "building_id": row.get("building_id", ""),
                "borough": row.get("borough", ""),
                "address": row.get("incident_address", ""),
                "probability": round(safe_float(row.get("model_probability")), 4),
                "equity_score": round(safe_float(row.get("equity_weighted_priority_score")), 4),
                "cumulative_prior": safe_int(row.get("cumulative_complaints_prior")),
                "open_violations": safe_int(row.get("open_linked_violation_count")),
                "why_risky": row.get("why_risky", ""),
            }
        )

    mix_rows = [{"borough": borough.title(), "count": count} for borough, count in borough_mix.most_common()]
    summary = {
        "top_n": len(rows),
        "avg_probability": round(avg_probability, 4),
        "avg_equity_score": round(avg_equity_score, 4),
        "avg_open_violations": round(avg_open_violations, 2),
    }
    return priority_top10, mix_rows, summary


def build_policy_summary(path: Path) -> dict[str, object]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("Policy simulation summary is empty.")
    grouped: dict[str, dict[str, dict[str, float | int | str]]] = defaultdict(dict)
    for row in rows:
        capacity = str(row.get("capacity", ""))
        policy = str(row.get("policy", ""))
        grouped[capacity][policy] = {
            "mean_hits": round(safe_float(row.get("mean_hits")), 4),
            "mean_precision": round(safe_float(row.get("mean_precision")), 4),
            "mean_recall": round(safe_float(row.get("mean_recall")), 4),
            "mean_lift": round(safe_float(row.get("mean_lift")), 4),
            "mean_avg_cre_vulnerability": round(safe_float(row.get("mean_avg_cre_vulnerability")), 4),
            "delta_hits_vs_random": round(safe_float(row.get("delta_hits_vs_random")), 4),
            "delta_hits_vs_history": round(safe_float(row.get("delta_hits_vs_history")), 4),
        }
    return grouped


def build_error_summary(path: Path) -> dict[str, object]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("Error analysis segments are empty.")

    def pick(segment_type: str, sort_key: str, reverse: bool = False) -> dict[str, object]:
        subset = [row for row in rows if row.get("segment_type") == segment_type]
        if not subset:
            raise ValueError(f"Missing error-analysis segment type: {segment_type}")
        ordered = sorted(subset, key=lambda row: safe_float(row.get(sort_key)), reverse=reverse)
        item = ordered[0]
        return {
            "segment_value": item.get("segment_value", ""),
            "metric": round(safe_float(item.get(sort_key)), 4),
            "rows": safe_int(item.get("rows")),
        }

    history_subset = [row for row in rows if row.get("segment_type") == "history_bucket"]
    history_top = max(history_subset, key=lambda row: safe_int(row.get("false_negatives")))
    return {
        "lowest_borough_recall": pick("borough", "recall", reverse=False),
        "highest_borough_recall": pick("borough", "recall", reverse=True),
        "lowest_cre_bucket_f1": pick("cre_bucket", "f1", reverse=False),
        "highest_history_false_negatives": {
            "segment_value": history_top.get("segment_value", ""),
            "metric": safe_int(history_top.get("false_negatives")),
            "rows": safe_int(history_top.get("rows")),
        },
    }


def build_uncertainty_summary(path: Path) -> dict[str, dict[str, float]]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("Uncertainty metrics table is empty.")
    summary: dict[str, dict[str, float]] = {}
    for row in rows:
        key = f"{row.get('metric_group')}::{row.get('metric')}"
        summary[key] = {
            "point_estimate": round(safe_float(row.get("point_estimate")), 6),
            "ci_low_95": round(safe_float(row.get("ci_low_95")), 6),
            "ci_high_95": round(safe_float(row.get("ci_high_95")), 6),
        }
    return summary


def build_drift_summary(path: Path) -> dict[str, object]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("Drift metrics table is empty.")
    numeric = [row for row in rows if row.get("feature_type") == "numeric"]
    categorical = [row for row in rows if row.get("feature_type") == "categorical"]
    top_numeric = sorted(numeric, key=lambda row: safe_float(row.get("drift_score")), reverse=True)[:3]
    top_categorical = sorted(categorical, key=lambda row: safe_float(row.get("drift_score")), reverse=True)[:2]
    return {
        "top_numeric": [
            {
                "feature": row.get("feature", ""),
                "drift_score": round(safe_float(row.get("drift_score")), 4),
                "train_mean": round(safe_float(row.get("train_mean")), 4),
                "test_mean": round(safe_float(row.get("test_mean")), 4),
            }
            for row in top_numeric
        ],
        "top_categorical": [
            {
                "feature": row.get("feature", ""),
                "drift_score": round(safe_float(row.get("drift_score")), 4),
                "note": row.get("note", ""),
            }
            for row in top_categorical
        ],
    }


def build_experiment_registry_summary(path: Path) -> dict[str, object]:
    rows = read_csv_rows(path)
    if not rows:
        raise ValueError("Experiment registry is empty.")
    model_names = sorted({row.get("model_name", "") for row in rows if row.get("model_name")})
    latest = max(rows, key=lambda row: row.get("artifact_modified_utc", ""))
    return {
        "row_count": len(rows),
        "model_names": model_names,
        "latest_model_name": latest.get("model_name", ""),
        "latest_artifact_modified_utc": latest.get("artifact_modified_utc", ""),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build synchronized presentation/brochure data for the NYC heating risk deck.")
    parser.add_argument(
        "--window-root",
        default=str(FINAL_WINDOW_ROOT),
        help="Heat-season window bundle root.",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "presentation_data.json"),
        help="Output JSON path for presentation data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    window_root = Path(args.window_root)
    raw_dir = window_root / "raw"
    processed_dir = window_root / "processed"
    reports_dir = window_root / "reports"
    models_dir = window_root / "models"

    complaints_path = raw_dir / "hpd_complaints_and_problems_heat.csv"
    sparse_panel_path = processed_dir / "building_day_heat_panel.csv"
    dense_panel_path = processed_dir / "building_day_heat_panel_dense.csv"
    weather_path = processed_dir / "noaa_gsod_nyc_daily_summary.csv"
    priority_path = reports_dir / "inspection_priority_latest_day.csv"
    profile_path = reports_dir / "heat_data_profile.md"
    rolling_path = reports_dir / "rolling_backtest_summary.md"
    logistic_metadata_path = models_dir / "logistic_regression_bundle.metadata.json"
    statistical_metrics_path = reports_dir / "statistical_model_metrics.md"
    seasonal_anova_path = reports_dir / "seasonal_anova.md"
    coefficients_path = reports_dir / "statistical_model_coefficients.csv"
    policy_summary_path = reports_dir / "inspection_policy_simulation_summary.csv"
    error_segments_path = reports_dir / "error_analysis_segments.csv"
    uncertainty_metrics_path = reports_dir / "uncertainty_metrics.csv"
    drift_metrics_path = reports_dir / "train_test_drift_metrics.csv"
    experiment_registry_path = reports_dir / "experiment_registry.csv"
    oot_validation_path = OOT_VALIDATION_REPORT_PATH

    complaint_rows = count_data_rows(complaints_path)
    sparse_rows = read_csv_rows(sparse_panel_path)
    unique_buildings = len({(row.get("building_id") or "").strip() for row in sparse_rows if (row.get("building_id") or "").strip()})
    dense_rows_from_profile, cre_rows = parse_profile_cre_coverage(profile_path)
    dense_rows = dense_rows_from_profile or count_data_rows(dense_panel_path)

    rolling = parse_rolling_backtest(rolling_path)
    logistic_metadata = json.loads(logistic_metadata_path.read_text(encoding="utf-8"))
    gee_test = parse_section_metrics(statistical_metrics_path, "GEE Test")
    glmm_test = parse_section_metrics(statistical_metrics_path, "GLMM Test")
    nb_test = parse_section_metrics(statistical_metrics_path, "NB Test")
    seasonal_anova = parse_seasonal_anova(seasonal_anova_path)
    glmm_random_intercept_sd = parse_glmm_random_intercept_sd(coefficients_path)

    priority_top10, priority_borough_mix, priority_summary = build_priority_outputs(priority_path)
    priority_rows = read_csv_rows(priority_path)
    monthly_trend = build_monthly_trend(complaints_path, sparse_panel_path, weather_path)
    borough_positive = build_borough_positive(sparse_panel_path)
    weather_effects = load_selected_effects(coefficients_path)
    policy_summary = build_policy_summary(policy_summary_path)
    error_summary = build_error_summary(error_segments_path)
    uncertainty_summary = build_uncertainty_summary(uncertainty_metrics_path)
    drift_summary = build_drift_summary(drift_metrics_path)
    experiment_registry_summary = build_experiment_registry_summary(experiment_registry_path)
    oot_summary = parse_out_of_time_validation(oot_validation_path)
    coefficient_rows = load_coefficient_detail_rows(coefficients_path)
    gee_cre = require_coefficient_row(coefficient_rows, "gee_logistic", "cre_vulnerability_index")
    glmm_cre = require_coefficient_row(coefficient_rows, "binomial_glmm", "cre_vulnerability_index")
    gee_recent = require_coefficient_row(coefficient_rows, "gee_logistic", "recent_complaint_flag")
    gee_heating = require_coefficient_row(coefficient_rows, "gee_logistic", "weather_heating_degree_scaled")
    gee_temp_drop = require_coefficient_row(coefficient_rows, "gee_logistic", "weather_temp_drop_c")
    nb_current = require_coefficient_row(coefficient_rows, "negative_binomial", "log1p_current_complaint_count")

    coldest = min(monthly_trend, key=lambda row: safe_float(row.get("avg_temp_c"))) if monthly_trend else {}
    busiest = max(monthly_trend, key=lambda row: safe_int(row.get("positive_buildings"))) if monthly_trend else {}

    data = {
        "headline_metrics": {
            "complaints": complaint_rows,
            "buildings": unique_buildings,
            "dense_rows": dense_rows,
            "priority_date": (priority_rows[0].get("calendar_date", "") if priority_rows else ""),
            "window_label": "2024-10-01 -> 2025-05-31",
            "cre_coverage_pct": round(cre_rows / dense_rows, 4) if dense_rows else 0.0,
        },
        "baseline_summary": rolling,
        "logistic_summary": {
            "threshold": logistic_metadata.get("threshold", 0),
            "calibration_method": logistic_metadata.get("calibration_method", "none"),
            "threshold_beta": logistic_metadata.get("threshold_beta", 1.0),
            "test_f1": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("f1")),
            "test_precision": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("precision")),
            "test_recall": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("recall")),
            "test_roc_auc": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("roc_auc")),
            "test_average_precision": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("average_precision")),
            "test_brier_score": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("brier_score")),
            "test_predicted_positive_rate": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("predicted_positive_rate")),
            "test_actual_positive_rate": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("actual_positive_rate")),
            "ranking_metrics": logistic_metadata.get("ranking_metrics", {}),
        },
        "gee_summary": {
            "test_f1": gee_test.get("f1", 0.0),
            "test_precision": gee_test.get("precision", 0.0),
            "test_recall": gee_test.get("recall", 0.0),
            "test_predicted_positive_rate": gee_test.get("predicted_positive_rate", 0.0),
            "test_actual_positive_rate": gee_test.get("actual_positive_rate", 0.0),
        },
        "glmm_summary": {
            "test_f1": glmm_test.get("f1", 0.0),
            "test_precision": glmm_test.get("precision", 0.0),
            "test_recall": glmm_test.get("recall", 0.0),
            "test_predicted_positive_rate": glmm_test.get("predicted_positive_rate", 0.0),
            "test_actual_positive_rate": glmm_test.get("actual_positive_rate", 0.0),
            "random_intercept_sd": glmm_random_intercept_sd,
        },
        "nb_summary": {
            "test_mae": nb_test.get("mae", 0.0),
            "test_rmse": nb_test.get("rmse", 0.0),
        },
        "daily_trend": monthly_trend,
        "season_summary": {
            "coldest_month": coldest,
            "busiest_month": busiest,
        },
        "borough_positive": borough_positive,
        "priority_top10": priority_top10,
        "priority_borough_mix": priority_borough_mix,
        "priority_summary": priority_summary,
        "policy_summary": policy_summary,
        "error_summary": error_summary,
        "uncertainty_summary": uncertainty_summary,
        "drift_summary": drift_summary,
        "experiment_registry_summary": experiment_registry_summary,
        "oot_summary": oot_summary,
        "seasonal_anova": seasonal_anova,
        "weather_effects": weather_effects,
        "inference_highlights": {
            "gee_cre": {
                "coef": round(safe_float(gee_cre.get("coefficient")), 4),
                "effect": round(safe_float(gee_cre.get("effect")), 4),
                "p_value": safe_float(gee_cre.get("p_value")),
            },
            "glmm_cre": {
                "coef": round(safe_float(glmm_cre.get("coefficient")), 4),
                "effect": round(safe_float(glmm_cre.get("effect")), 4),
                "p_value": safe_float(glmm_cre.get("p_value")),
            },
            "gee_recent_complaint": {
                "coef": round(safe_float(gee_recent.get("coefficient")), 4),
                "effect": round(safe_float(gee_recent.get("effect")), 4),
                "p_value": safe_float(gee_recent.get("p_value")),
            },
            "gee_heating_degree": {
                "coef": round(safe_float(gee_heating.get("coefficient")), 4),
                "effect": round(safe_float(gee_heating.get("effect")), 4),
                "p_value": safe_float(gee_heating.get("p_value")),
            },
            "gee_temp_drop": {
                "coef": round(safe_float(gee_temp_drop.get("coefficient")), 4),
                "effect": round(safe_float(gee_temp_drop.get("effect")), 4),
                "p_value": safe_float(gee_temp_drop.get("p_value")),
            },
            "nb_current_count": {
                "coef": round(safe_float(nb_current.get("coefficient")), 4),
                "effect": round(safe_float(nb_current.get("effect")), 4),
                "p_value": safe_float(nb_current.get("p_value")),
            },
        },
        "model_comparison": [
            {
                "model": "Calibrated Logistic",
                "test_f1": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("f1")),
                "test_precision": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("precision")),
                "test_recall": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("recall")),
                "test_roc_auc": safe_float(logistic_metadata.get("metrics", {}).get("test", {}).get("roc_auc")),
            },
            {
                "model": "GEE Logistic",
                "test_f1": gee_test.get("f1", 0.0),
                "test_precision": gee_test.get("precision", 0.0),
                "test_recall": gee_test.get("recall", 0.0),
                "test_roc_auc": 0.0,
            },
            {
                "model": "GLMM diagnostic",
                "test_f1": glmm_test.get("f1", 0.0),
                "test_precision": glmm_test.get("precision", 0.0),
                "test_recall": glmm_test.get("recall", 0.0),
                "test_roc_auc": 0.0,
            },
        ],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote presentation data to {output_path}", flush=True)


if __name__ == "__main__":
    main()
