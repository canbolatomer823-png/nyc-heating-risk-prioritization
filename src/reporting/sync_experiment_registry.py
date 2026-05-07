from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_EXPERIMENT_REGISTRY_PATH,
    FINAL_LOGISTIC_METRICS_PATH,
    FINAL_LOGISTIC_RANKING_METRICS_PATH,
    FINAL_MODEL_METADATA_PATH,
    FINAL_REPORTS_DIR,
    FINAL_STATISTICAL_METRICS_PATH,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync an experiment registry from current project artifacts.")
    parser.add_argument(
        "--output",
        default=str(FINAL_EXPERIMENT_REGISTRY_PATH),
        help="CSV output path for the experiment registry.",
    )
    parser.add_argument(
        "--window-label",
        default="2024-10-01 -> 2025-05-31",
        help="Human-readable window label written into the registry.",
    )
    return parser.parse_args()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def parse_section(text: str, title: str) -> dict[str, str]:
    match = re.search(rf"## {re.escape(title)}\n(.*?)(?:\n## |\Z)", text, flags=re.S)
    if not match:
        raise ValueError(f"Missing section: {title}")
    block = match.group(1)
    values: dict[str, str] = {}
    for line in block.splitlines():
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            values[key.strip()] = value.strip()
    return values


def parse_backtest_rows(path: Path, window_label: str) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    for model_key, model_name in [
        ("baseline", "baseline_backtest"),
        ("sgd_logistic_regression", "sgd_logistic_backtest"),
    ]:
        match = re.search(
            rf"### {re.escape(model_key)}\n- Mean F1: ([0-9.]+)\n- Mean ROC AUC: ([0-9.]+)\n- Mean average precision: ([0-9.]+)\n- Mean precision: ([0-9.]+)\n- Mean recall: ([0-9.]+)",
            text,
        )
        if not match:
            continue
        rows.append(
            {
                "experiment_id": f"{model_name}:{int(path.stat().st_mtime)}",
                "model_name": model_name,
                "evaluation_scope": "rolling_backtest",
                "source_artifact": str(path),
                "artifact_modified_utc": iso_mtime(path),
                "window_label": window_label,
                "threshold": "",
                "test_f1": match.group(1),
                "test_precision": match.group(4),
                "test_recall": match.group(5),
                "test_roc_auc": match.group(2),
                "average_precision": match.group(3),
                "precision_at_50": "",
                "lift_at_50": "",
                "test_mae": "",
                "notes": "expanding monthly backtest summary",
            }
        )
    return rows


def parse_logistic_row(metadata_path: Path, metrics_path: Path, ranking_path: Path, window_label: str) -> dict[str, str]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    test_metrics = metadata["metrics"]["test"]
    ranking = metadata["ranking_metrics"]["50"]
    return {
        "experiment_id": f"calibrated_logistic:{metadata['created_at_utc']}",
        "model_name": "calibrated_logistic",
        "evaluation_scope": "held_out_test",
        "source_artifact": str(metrics_path),
        "artifact_modified_utc": iso_mtime(metrics_path),
        "window_label": window_label,
        "threshold": str(metadata["threshold"]),
        "test_f1": str(test_metrics["f1"]),
        "test_precision": str(test_metrics["precision"]),
        "test_recall": str(test_metrics["recall"]),
        "test_roc_auc": str(test_metrics["roc_auc"]),
        "average_precision": str(test_metrics["average_precision"]),
        "precision_at_50": str(ranking["mean_precision_at_k"]),
        "lift_at_50": str(ranking["mean_lift_at_k"]),
        "test_mae": "",
        "notes": f"ranking metrics source={ranking_path}",
    }


def parse_statistical_rows(path: Path, window_label: str) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []
    mapping = [
        ("GEE Test", "gee_logistic", "0.25", "held_out_sampled"),
        ("GLMM Test", "binomial_glmm", "0.4", "held_out_full_split_stratified_sample"),
    ]
    for title, name, threshold, scope in mapping:
        metrics = parse_section(text, title)
        rows.append(
            {
                "experiment_id": f"{name}:{int(path.stat().st_mtime)}",
                "model_name": name,
                "evaluation_scope": scope,
                "source_artifact": str(path),
                "artifact_modified_utc": iso_mtime(path),
                "window_label": window_label,
                "threshold": threshold,
                "test_f1": metrics.get("f1", ""),
                "test_precision": metrics.get("precision", ""),
                "test_recall": metrics.get("recall", ""),
                "test_roc_auc": "",
                "average_precision": "",
                "precision_at_50": "",
                "lift_at_50": "",
                "test_mae": "",
                "notes": title,
            }
        )

    nb_metrics = parse_section(text, "NB Test")
    rows.append(
        {
            "experiment_id": f"negative_binomial:{int(path.stat().st_mtime)}",
            "model_name": "negative_binomial",
            "evaluation_scope": "held_out_sampled_count",
            "source_artifact": str(path),
            "artifact_modified_utc": iso_mtime(path),
            "window_label": window_label,
            "threshold": "",
            "test_f1": "",
            "test_precision": "",
            "test_recall": "",
            "test_roc_auc": "",
            "average_precision": "",
            "precision_at_50": "",
            "lift_at_50": "",
            "test_mae": nb_metrics.get("mae", ""),
            "notes": "NB Test",
        }
    )
    return rows


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_registry(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "experiment_id",
        "model_name",
        "evaluation_scope",
        "source_artifact",
        "artifact_modified_utc",
        "window_label",
        "threshold",
        "test_f1",
        "test_precision",
        "test_recall",
        "test_roc_auc",
        "average_precision",
        "precision_at_50",
        "lift_at_50",
        "test_mae",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)

    current_rows: list[dict[str, str]] = []
    current_rows.extend(parse_backtest_rows(FINAL_REPORTS_DIR / "rolling_backtest_summary.md", args.window_label))
    current_rows.append(
        parse_logistic_row(
            FINAL_MODEL_METADATA_PATH,
            FINAL_LOGISTIC_METRICS_PATH,
            FINAL_LOGISTIC_RANKING_METRICS_PATH,
            args.window_label,
        )
    )
    current_rows.extend(parse_statistical_rows(FINAL_STATISTICAL_METRICS_PATH, args.window_label))

    current_model_names = {row["model_name"] for row in current_rows}
    merged: dict[str, dict[str, str]] = {}
    for row in read_existing(output_path):
        if row.get("model_name") in current_model_names:
            continue
        merged[row["experiment_id"]] = row
    for row in current_rows:
        merged[row["experiment_id"]] = row

    ordered = sorted(
        merged.values(),
        key=lambda row: (row["artifact_modified_utc"], row["model_name"]),
    )
    write_registry(output_path, ordered)
    print(f"wrote experiment registry to {output_path}", flush=True)


if __name__ == "__main__":
    main()
