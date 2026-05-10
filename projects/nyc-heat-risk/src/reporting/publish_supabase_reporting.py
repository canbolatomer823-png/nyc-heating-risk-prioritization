from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_MODEL_METADATA_PATH, FINAL_PRIORITY_CSV_PATH, FINAL_REPORTS_DIR, FINAL_WINDOW_NAME


PROJECT_NAME = "nyc-heat-risk"
DEFAULT_OUTPUT_DIR = FINAL_REPORTS_DIR / "supabase"
DEFAULT_DEMO_PROOF_DIR = Path(__file__).resolve().parents[2] / "reports" / "demo_proof"
PUBLISH_RECEIPT_FILENAME = "supabase_publish_receipt.md"


def safe_float(value: str | int | float | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: str | int | float | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def clean_text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_json_array(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_priority_rows(path: Path, top_n: int | None = None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[:top_n] if top_n else rows


def build_model_run_id(window_label: str, priority_date: str, metadata: dict[str, Any], rows: list[dict[str, str]]) -> str:
    digest_source = {
        "window_label": window_label,
        "priority_date": priority_date,
        "model_type": metadata.get("model_type", ""),
        "created_at_utc": metadata.get("created_at_utc", ""),
        "row_count": len(rows),
        "top_building": rows[0].get("building_id", "") if rows else "",
    }
    digest = hashlib.sha256(json.dumps(digest_source, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    return f"{PROJECT_NAME}-{priority_date}-{digest}"


def build_reporting_payload(
    priority_csv_path: Path,
    metadata_json_path: Path,
    window_label: str = FINAL_WINDOW_NAME,
    top_n: int | None = None,
    demo_proof_dir: Path | None = DEFAULT_DEMO_PROOF_DIR,
) -> dict[str, Any]:
    rows = read_priority_rows(priority_csv_path, top_n=top_n)
    metadata = read_json(metadata_json_path)
    priority_date = rows[0].get("calendar_date", "") if rows else ""
    model_run_id = build_model_run_id(window_label, priority_date, metadata, rows)
    test_rows = metadata.get("metrics", {}).get("test", {}).get("rows")

    model_run = {
        "model_run_id": model_run_id,
        "project_name": PROJECT_NAME,
        "window_label": window_label,
        "priority_date": priority_date,
        "model_type": metadata.get("model_type", "unknown"),
        "calibration_method": metadata.get("calibration_method"),
        "model_threshold": safe_float(metadata.get("threshold")),
        "scored_row_count": safe_int(test_rows),
        "priority_row_count": len(rows),
        "source_priority_csv": str(priority_csv_path),
        "source_metadata_json": str(metadata_json_path),
        "created_at_utc": metadata.get("created_at_utc"),
        "notes": "Operational Supabase/Postgres reporting layer for inspection priority demo.",
    }

    priority_buildings: list[dict[str, Any]] = []
    prediction_explanations: list[dict[str, Any]] = []
    for row in rows:
        rank = safe_int(row.get("inspection_priority_rank"))
        priority_buildings.append(
            {
                "model_run_id": model_run_id,
                "priority_date": row.get("calendar_date"),
                "inspection_priority_rank": rank,
                "building_id": clean_text(row.get("building_id")),
                "building_bbl": clean_text(row.get("building_bbl")),
                "borough": clean_text(row.get("borough")),
                "incident_address": clean_text(row.get("incident_address")),
                "building_zip": clean_text(row.get("building_zip")),
                "community_board": clean_text(row.get("community_board")),
                "census_tract": clean_text(row.get("census_tract")),
                "raw_model_probability": safe_float(row.get("raw_model_probability")),
                "model_probability": safe_float(row.get("model_probability")),
                "model_threshold": safe_float(row.get("model_threshold")),
                "model_prediction": safe_int(row.get("model_prediction")),
                "equity_weighted_priority_score": safe_float(row.get("equity_weighted_priority_score")),
                "cre_vulnerability_index": safe_float(row.get("cre_vulnerability_index")),
                "cre_high_vulnerability_flag": safe_int(row.get("cre_high_vulnerability_flag")),
                "open_linked_violation_count": safe_int(row.get("open_linked_violation_count")),
                "cumulative_complaints_prior": safe_int(row.get("cumulative_complaints_prior")),
                "days_since_last_complaint_capped": safe_float(row.get("days_since_last_complaint_capped")),
                "heat_sensor_program_flag": safe_int(row.get("heat_sensor_program_flag")),
                "heat_sensor_active_flag": safe_int(row.get("heat_sensor_active_flag")),
                "weather_heating_degree_c": safe_float(row.get("weather_heating_degree_c")),
                "weather_freezing_any_flag": safe_int(row.get("weather_freezing_any_flag")),
            }
        )
        prediction_explanations.append(
            {
                "model_run_id": model_run_id,
                "priority_date": row.get("calendar_date"),
                "inspection_priority_rank": rank,
                "building_id": clean_text(row.get("building_id")),
                "why_risky": row.get("why_risky", ""),
                "top_positive_contributors": row.get("top_positive_contributors"),
                "top_negative_contributors": row.get("top_negative_contributors"),
                "top_positive_contributors_json": parse_json_array(row.get("top_positive_contributors_json")),
                "top_negative_contributors_json": parse_json_array(row.get("top_negative_contributors_json")),
            }
        )

    demo_events = build_demo_events(model_run_id, demo_proof_dir)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_run": model_run,
        "daily_priority_buildings": priority_buildings,
        "prediction_explanations": prediction_explanations,
        "demo_proof_events": demo_events,
    }


def build_demo_events(model_run_id: str, demo_proof_dir: Path | None) -> list[dict[str, Any]]:
    if demo_proof_dir is None or not demo_proof_dir.exists():
        return []

    event_files = {
        "health": "health.json",
        "metadata": "metadata.json",
        "priorities_top5": "priorities_top5.json",
        "dashboard": "dashboard_status.json",
        "record_lookup_top1": "record_lookup_top1.json",
        "score_response": "score_response.json",
    }
    events: list[dict[str, Any]] = []
    for event_type, filename in event_files.items():
        path = demo_proof_dir / filename
        if path.exists():
            events.append(
                {
                    "model_run_id": model_run_id,
                    "event_type": event_type,
                    "payload": read_json(path),
                }
            )
    return events


def write_payload_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / "supabase_reporting_payload.json"
    summary_path = output_dir / "supabase_reporting_summary.md"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    model_run = payload["model_run"]
    top_rows = payload["daily_priority_buildings"][:5]
    lines = [
        "# Supabase Reporting Payload",
        "",
        f"- Model run: `{model_run['model_run_id']}`",
        f"- Priority date: `{model_run['priority_date']}`",
        f"- Priority rows: `{model_run['priority_row_count']}`",
        f"- Demo proof events: `{len(payload['demo_proof_events'])}`",
        "",
        "## Top rows",
    ]
    for row in top_rows:
        lines.append(
            "- "
            + " | ".join(
                [
                    f"rank={row['inspection_priority_rank']}",
                    f"building_id={row['building_id']}",
                    f"borough={row['borough']}",
                    f"prob={round(row['model_probability'] or 0.0, 4)}",
                    f"equity={round(row['equity_weighted_priority_score'] or 0.0, 4)}",
                ]
            )
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_payload(db_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise SystemExit("Missing dependency: install psycopg[binary] or run `pip install -r requirements.txt`.") from exc

    model_run = payload["model_run"]
    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO nhr.model_runs (
                    model_run_id, project_name, window_label, priority_date, model_type,
                    calibration_method, model_threshold, scored_row_count, priority_row_count,
                    source_priority_csv, source_metadata_json, created_at_utc, notes
                )
                VALUES (
                    %(model_run_id)s, %(project_name)s, %(window_label)s, %(priority_date)s, %(model_type)s,
                    %(calibration_method)s, %(model_threshold)s, %(scored_row_count)s, %(priority_row_count)s,
                    %(source_priority_csv)s, %(source_metadata_json)s, %(created_at_utc)s, %(notes)s
                )
                ON CONFLICT (model_run_id) DO UPDATE SET
                    priority_row_count = EXCLUDED.priority_row_count,
                    scored_row_count = EXCLUDED.scored_row_count,
                    published_at = now(),
                    notes = EXCLUDED.notes
                """,
                model_run,
            )
            cursor.execute("DELETE FROM nhr.prediction_explanations WHERE model_run_id = %s", (model_run["model_run_id"],))
            cursor.execute("DELETE FROM nhr.daily_priority_buildings WHERE model_run_id = %s", (model_run["model_run_id"],))
            cursor.execute("DELETE FROM nhr.demo_proof_events WHERE model_run_id = %s", (model_run["model_run_id"],))

            priority_columns = [
                "model_run_id",
                "priority_date",
                "inspection_priority_rank",
                "building_id",
                "building_bbl",
                "borough",
                "incident_address",
                "building_zip",
                "community_board",
                "census_tract",
                "raw_model_probability",
                "model_probability",
                "model_threshold",
                "model_prediction",
                "equity_weighted_priority_score",
                "cre_vulnerability_index",
                "cre_high_vulnerability_flag",
                "open_linked_violation_count",
                "cumulative_complaints_prior",
                "days_since_last_complaint_capped",
                "heat_sensor_program_flag",
                "heat_sensor_active_flag",
                "weather_heating_degree_c",
                "weather_freezing_any_flag",
            ]
            cursor.executemany(
                f"""
                INSERT INTO nhr.daily_priority_buildings ({", ".join(priority_columns)})
                VALUES ({", ".join(["%s"] * len(priority_columns))})
                """,
                [[row[column] for column in priority_columns] for row in payload["daily_priority_buildings"]],
            )

            explanation_columns = [
                "model_run_id",
                "priority_date",
                "inspection_priority_rank",
                "building_id",
                "why_risky",
                "top_positive_contributors",
                "top_negative_contributors",
                "top_positive_contributors_json",
                "top_negative_contributors_json",
            ]
            cursor.executemany(
                f"""
                INSERT INTO nhr.prediction_explanations ({", ".join(explanation_columns)})
                VALUES ({", ".join(["%s"] * len(explanation_columns))})
                """,
                [
                    [
                        Jsonb(row[column]) if column.endswith("_json") else row[column]
                        for column in explanation_columns
                    ]
                    for row in payload["prediction_explanations"]
                ],
            )

            cursor.executemany(
                """
                INSERT INTO nhr.demo_proof_events (model_run_id, event_type, payload)
                VALUES (%s, %s, %s)
                """,
                [
                    [event["model_run_id"], event["event_type"], Jsonb(event["payload"])]
                    for event in payload["demo_proof_events"]
                ],
            )
            cursor.execute("select count(*) from nhr.daily_priority_buildings where model_run_id = %s", (model_run["model_run_id"],))
            priority_count = int(cursor.fetchone()[0])
            cursor.execute("select count(*) from nhr.prediction_explanations where model_run_id = %s", (model_run["model_run_id"],))
            explanation_count = int(cursor.fetchone()[0])
            cursor.execute("select count(*) from nhr.demo_proof_events where model_run_id = %s", (model_run["model_run_id"],))
            demo_event_count = int(cursor.fetchone()[0])
            cursor.execute("select count(*) from nhr.model_runs")
            total_model_runs = int(cursor.fetchone()[0])

    return {
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_run_id": model_run["model_run_id"],
        "priority_rows": priority_count,
        "explanation_rows": explanation_count,
        "demo_events": demo_event_count,
        "total_model_runs": total_model_runs,
    }


def write_publish_receipt(receipt: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / PUBLISH_RECEIPT_FILENAME
    lines = [
        "# Supabase Publish Receipt",
        "",
        f"- Published at: `{receipt['published_at_utc']}`",
        f"- Model run: `{receipt['model_run_id']}`",
        f"- Priority rows written: `{receipt['priority_rows']}`",
        f"- Explanation rows written: `{receipt['explanation_rows']}`",
        f"- Demo events written: `{receipt['demo_events']}`",
        f"- Total model runs in database: `{receipt['total_model_runs']}`",
        "",
        "## Interpretation",
        "",
        "This receipt is written only after the local publisher successfully inserts the reporting payload into Supabase/Postgres.",
        "It proves the operational SQL layer contains the final model run, top-risk building rows, row-level explanations, and demo proof events.",
        "",
    ]
    receipt_path.write_text("\n".join(lines), encoding="utf-8")
    return receipt_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish final priority/reporting artifacts to a Supabase Postgres schema.")
    parser.add_argument("--priority-csv", default=str(FINAL_PRIORITY_CSV_PATH))
    parser.add_argument("--metadata-json", default=str(FINAL_MODEL_METADATA_PATH))
    parser.add_argument("--window-label", default=FINAL_WINDOW_NAME)
    parser.add_argument("--top-n", type=int, default=None)
    parser.add_argument("--demo-proof-dir", default=str(DEFAULT_DEMO_PROOF_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--db-url", default=os.environ.get("SUPABASE_DB_URL", ""))
    parser.add_argument("--publish", action="store_true", help="Write to Supabase/Postgres. Without this, only local payload files are written.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_reporting_payload(
        priority_csv_path=Path(args.priority_csv),
        metadata_json_path=Path(args.metadata_json),
        window_label=args.window_label,
        top_n=args.top_n,
        demo_proof_dir=Path(args.demo_proof_dir) if args.demo_proof_dir else None,
    )
    write_payload_outputs(payload, Path(args.output_dir))
    if args.publish:
        if not args.db_url:
            raise SystemExit("SUPABASE_DB_URL is required when --publish is used.")
        receipt = publish_payload(args.db_url, payload)
        receipt_path = write_publish_receipt(receipt, Path(args.output_dir))
        print(f"supabase publish receipt written: {receipt_path}")
    print(
        "supabase reporting payload ready: "
        f"model_run_id={payload['model_run']['model_run_id']} "
        f"priority_rows={len(payload['daily_priority_buildings'])} "
        f"demo_events={len(payload['demo_proof_events'])}"
    )


if __name__ == "__main__":
    main()
