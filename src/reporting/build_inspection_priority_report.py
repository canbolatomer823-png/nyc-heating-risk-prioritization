from __future__ import annotations

import argparse
import csv
import heapq
import json
from collections import Counter
from pathlib import Path
import sys

import joblib

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.feature_explanations import explain_model_rows
from project_paths import (
    FINAL_MODEL_BUNDLE_PATH,
    FINAL_PRIORITY_CSV_PATH,
    FINAL_PRIORITY_EXPLANATIONS_PATH,
    FINAL_PRIORITY_EXPLANATIONS_SUMMARY_PATH,
    FINAL_PRIORITY_SUMMARY_PATH,
    FINAL_SCORED_CSV_PATH,
)


def safe_float(value: str | None) -> float:
    try:
        return float(value or "0")
    except Exception:
        return 0.0


def safe_int(value: str | None) -> int:
    try:
        return int(value or "0")
    except Exception:
        return 0


def with_equity_score(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    equity_weighted_score = safe_float(updated.get("model_probability")) * (
        1.0 + safe_float(updated.get("cre_vulnerability_index"))
    )
    updated["equity_weighted_priority_score"] = f"{round(equity_weighted_score, 6):.6f}"
    return updated


def latest_priority_rows_from_csv(path: Path, top_n: int) -> tuple[str, list[dict[str, str]]]:
    latest_date = "n/a"
    top_rows_heap: list[tuple[float, str, dict[str, str]]] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            if raw_row.get("data_split") != "test":
                continue

            calendar_date = (raw_row.get("calendar_date") or "").strip()
            if not calendar_date:
                continue

            row = with_equity_score(raw_row)
            equity_score = safe_float(row.get("equity_weighted_priority_score"))
            tie_breaker = (row.get("building_id") or "").strip()
            heap_item = (equity_score, tie_breaker, row)

            if latest_date == "n/a" or calendar_date > latest_date:
                latest_date = calendar_date
                top_rows_heap = [heap_item]
                continue

            if calendar_date < latest_date:
                continue

            if len(top_rows_heap) < top_n:
                heapq.heappush(top_rows_heap, heap_item)
                continue

            if heap_item[:2] > top_rows_heap[0][:2]:
                heapq.heapreplace(top_rows_heap, heap_item)

    if latest_date == "n/a":
        return latest_date, []

    ordered_rows = [item[2] for item in sorted(top_rows_heap, key=lambda item: (item[0], item[1]), reverse=True)]
    return latest_date, ordered_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def enrich_with_explanations(rows: list[dict[str, str]], model_bundle_path: Path) -> list[dict[str, str]]:
    if not rows or not model_bundle_path.exists():
        return rows

    bundle = joblib.load(model_bundle_path)
    model = bundle["model"]
    metadata = bundle["metadata"]
    explanations = explain_model_rows(model=model, metadata=metadata, rows=rows, top_n=5)

    enriched: list[dict[str, str]] = []
    for row, explanation in zip(rows, explanations):
        updated = dict(row)
        updated["why_risky"] = str(explanation["why_risky"])
        updated["top_positive_contributors"] = str(explanation["top_positive_contributors_text"])
        updated["top_negative_contributors"] = str(explanation["top_negative_contributors_text"])
        updated["top_positive_contributors_json"] = json.dumps(explanation["top_positive_contributors"], ensure_ascii=False)
        updated["top_negative_contributors_json"] = json.dumps(explanation["top_negative_contributors"], ensure_ascii=False)
        enriched.append(updated)
    return enriched


def explanation_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected_columns = [
        "inspection_priority_rank",
        "calendar_date",
        "building_id",
        "borough",
        "incident_address",
        "model_probability",
        "equity_weighted_priority_score",
        "why_risky",
        "top_positive_contributors",
        "top_negative_contributors",
    ]
    return [{column: row.get(column, "") for column in selected_columns} for row in rows]


def write_explanation_summary(path: Path, latest_date: str, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Why Risky Explanations",
        "",
        f"- Priority list date: {latest_date}",
        f"- Explained rows: {len(rows)}",
        "- Method: logistic model feature contributions in preprocessed logit space; calibrated probability is still used for ranking.",
        "- Interpretation: positive contributors increase the raw risk score; negative contributors reduce it.",
        "",
        "## Top explained buildings",
    ]
    for row in rows[:10]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"rank={row.get('inspection_priority_rank', '')}",
                    f"building_id={row.get('building_id', '')}",
                    f"borough={row.get('borough', '')}",
                    f"prob={round(safe_float(row.get('model_probability')), 4)}",
                    f"why={row.get('why_risky', '')}",
                ]
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(path: Path, latest_date: str, rows: list[dict[str, str]]) -> None:
    borough_counts = Counter((row.get("borough") or "").strip() for row in rows)
    hsp_count = sum(safe_int(row.get("heat_sensor_active_flag")) > 0 for row in rows)
    avg_probability = sum(safe_float(row.get("model_probability")) for row in rows) / len(rows) if rows else 0.0
    avg_equity_weighted_score = sum(safe_float(row.get("equity_weighted_priority_score")) for row in rows) / len(rows) if rows else 0.0
    avg_open_violations = sum(safe_int(row.get("open_linked_violation_count")) for row in rows) / len(rows) if rows else 0.0
    avg_cre_vulnerability = sum(safe_float(row.get("cre_vulnerability_index")) for row in rows) / len(rows) if rows else 0.0

    lines = [
        "# Inspection Priority Summary",
        "",
        f"- Priority list date: {latest_date}",
        f"- Top buildings included: {len(rows)}",
        f"- Average predicted next-day complaint probability: {round(avg_probability, 4)}",
        f"- Average equity-weighted priority score: {round(avg_equity_weighted_score, 4)}",
        f"- Average open linked violation count: {round(avg_open_violations, 2)}",
        f"- Average CRE vulnerability index: {round(avg_cre_vulnerability, 4)}",
        f"- Active Heat Sensor Program buildings in top list: {hsp_count}",
        "",
        "## Borough mix",
    ]
    for borough, count in borough_counts.most_common():
        lines.append(f"- {borough}: {count}")

    lines.append("")
    lines.append("## Top 10 buildings")
    for row in rows[:10]:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"rank={row.get('inspection_priority_rank', '')}",
                    f"building_id={row.get('building_id', '')}",
                    f"borough={row.get('borough', '')}",
                    f"address={row.get('incident_address', '')}",
                    f"prob={round(safe_float(row.get('model_probability')), 4)}",
                    f"equity_score={round(safe_float(row.get('equity_weighted_priority_score')), 4)}",
                    f"cre_vulnerability={round(safe_float(row.get('cre_vulnerability_index')), 4)}",
                    f"open_violations={safe_int(row.get('open_linked_violation_count'))}",
                    f"cumulative_prior={safe_int(row.get('cumulative_complaints_prior'))}",
                    f"heat_sensor_active={safe_int(row.get('heat_sensor_active_flag'))}",
                ]
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a latest-day inspection priority report from logistic model scores.")
    parser.add_argument(
        "--input",
        default=str(FINAL_SCORED_CSV_PATH),
        help="Row-level logistic model scores.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=50,
        help="Number of buildings to keep in the priority list.",
    )
    parser.add_argument(
        "--csv-output",
        default=str(FINAL_PRIORITY_CSV_PATH),
        help="CSV output path for the ranked priority list.",
    )
    parser.add_argument(
        "--summary-output",
        default=str(FINAL_PRIORITY_SUMMARY_PATH),
        help="Markdown output path for the summary report.",
    )
    parser.add_argument(
        "--model-bundle",
        default=str(FINAL_MODEL_BUNDLE_PATH),
        help="Fitted logistic model bundle used to generate why-risky explanations.",
    )
    parser.add_argument(
        "--explanations-output",
        default=str(FINAL_PRIORITY_EXPLANATIONS_PATH),
        help="CSV output path for row-level why-risky explanations.",
    )
    parser.add_argument(
        "--explanations-summary-output",
        default=str(FINAL_PRIORITY_EXPLANATIONS_SUMMARY_PATH),
        help="Markdown output path for the why-risky explanation summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    latest_date, priority_rows = latest_priority_rows_from_csv(Path(args.input), args.top_n)

    ranked_rows: list[dict[str, str]] = []
    for rank, row in enumerate(priority_rows, start=1):
        row = dict(row)
        row["inspection_priority_rank"] = str(rank)
        ranked_rows.append(row)
    ranked_rows = enrich_with_explanations(ranked_rows, Path(args.model_bundle))

    write_csv(Path(args.csv_output), ranked_rows)
    write_summary(Path(args.summary_output), latest_date, ranked_rows)
    write_csv(Path(args.explanations_output), explanation_rows(ranked_rows))
    write_explanation_summary(Path(args.explanations_summary_output), latest_date, ranked_rows)
    print(f"wrote ranked priorities to {args.csv_output}", flush=True)
    print(f"wrote summary to {args.summary_output}", flush=True)
    print(f"wrote why-risky explanations to {args.explanations_output}", flush=True)
    print(f"wrote why-risky summary to {args.explanations_summary_output}", flush=True)


if __name__ == "__main__":
    main()
