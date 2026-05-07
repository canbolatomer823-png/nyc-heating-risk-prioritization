from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import FINAL_REPORTS_DIR, PROJECT_ROOT


SUPABASE_DIR = FINAL_REPORTS_DIR / "supabase"
DEFAULT_SCHEMA_SQL = PROJECT_ROOT / "sql" / "05_supabase_reporting_schema.sql"
DEFAULT_PAYLOAD_JSON = SUPABASE_DIR / "supabase_reporting_payload.json"
DEFAULT_SUMMARY_MD = SUPABASE_DIR / "supabase_reporting_summary.md"
DEFAULT_REPORT_MD = SUPABASE_DIR / "supabase_readiness.md"

EXPECTED_TABLES = {
    "model_runs",
    "daily_priority_buildings",
    "prediction_explanations",
    "demo_proof_events",
}
EXPECTED_VIEWS = {
    "latest_model_run",
    "latest_priority_with_explanations",
    "latest_borough_priority_mix",
}


@dataclass
class CheckResult:
    status: str
    check: str
    detail: str


def add(results: list[CheckResult], status: str, check: str, detail: str) -> None:
    results.append(CheckResult(status=status, check=check, detail=detail))


def mask_db_url(db_url: str) -> str:
    if not db_url:
        return ""
    parsed = urlsplit(db_url)
    if not parsed.netloc:
        return "provided"
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    username = parsed.username or ""
    auth = f"{username}:***@" if username else ""
    return urlunsplit((parsed.scheme, f"{auth}{hostname}{port}", parsed.path, "", ""))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_local_files(schema_sql: Path, payload_json: Path, summary_md: Path, results: list[CheckResult]) -> dict[str, Any] | None:
    if schema_sql.exists() and schema_sql.stat().st_size > 100:
        add(results, "OK", "schema sql", f"{schema_sql} ({schema_sql.stat().st_size:,} bytes)")
    else:
        add(results, "FAIL", "schema sql", f"missing or too small: {schema_sql}")

    if summary_md.exists() and summary_md.stat().st_size > 100:
        add(results, "OK", "local summary", f"{summary_md} ({summary_md.stat().st_size:,} bytes)")
    else:
        add(results, "FAIL", "local summary", f"missing or too small: {summary_md}")

    if not payload_json.exists():
        add(results, "FAIL", "local payload", f"missing: {payload_json}")
        return None

    try:
        payload = load_json(payload_json)
    except json.JSONDecodeError as exc:
        add(results, "FAIL", "local payload", f"invalid JSON: {exc}")
        return None

    add(results, "OK", "local payload", f"{payload_json} ({payload_json.stat().st_size:,} bytes)")
    return payload


def validate_payload_shape(payload: dict[str, Any], results: list[CheckResult]) -> None:
    model_run = payload.get("model_run") or {}
    priority_rows = payload.get("daily_priority_buildings") or []
    explanation_rows = payload.get("prediction_explanations") or []
    demo_events = payload.get("demo_proof_events") or []

    if model_run.get("model_run_id") and model_run.get("priority_date"):
        add(results, "OK", "model_run payload", f"{model_run['model_run_id']} / {model_run['priority_date']}")
    else:
        add(results, "FAIL", "model_run payload", "missing model_run_id or priority_date")

    if len(priority_rows) == 50:
        add(results, "OK", "priority payload rows", "50 rows")
    else:
        add(results, "FAIL", "priority payload rows", f"{len(priority_rows)} rows, expected 50")

    if len(explanation_rows) == 50:
        add(results, "OK", "explanation payload rows", "50 rows")
    else:
        add(results, "FAIL", "explanation payload rows", f"{len(explanation_rows)} rows, expected 50")

    if len(demo_events) >= 5:
        event_types = ", ".join(sorted(str(event.get("event_type")) for event in demo_events))
        add(results, "OK", "demo event payload rows", f"{len(demo_events)} events: {event_types}")
    else:
        add(results, "FAIL", "demo event payload rows", f"{len(demo_events)} events, expected at least 5")

    if priority_rows and priority_rows[0].get("model_probability") is not None and priority_rows[0].get("building_id"):
        add(results, "OK", "top priority payload", f"building_id={priority_rows[0]['building_id']}")
    else:
        add(results, "FAIL", "top priority payload", "missing building_id or probability")


def check_database(db_url: str, results: list[CheckResult], payload: dict[str, Any] | None = None) -> None:
    try:
        import psycopg
    except ImportError as exc:
        add(results, "FAIL", "psycopg dependency", f"missing: {exc}")
        return

    try:
        with psycopg.connect(db_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select current_database(), current_schema()")
                database_name, schema_name = cursor.fetchone()
                add(results, "OK", "database connection", f"database={database_name}, default_schema={schema_name}")

                cursor.execute(
                    """
                    select table_name
                    from information_schema.tables
                    where table_schema = 'nhr'
                      and table_type = 'BASE TABLE'
                    """
                )
                tables = {row[0] for row in cursor.fetchall()}
                missing_tables = sorted(EXPECTED_TABLES - tables)
                if missing_tables:
                    add(results, "FAIL", "Supabase tables", f"missing: {', '.join(missing_tables)}")
                else:
                    add(results, "OK", "Supabase tables", ", ".join(sorted(EXPECTED_TABLES)))

                cursor.execute(
                    """
                    select table_name
                    from information_schema.views
                    where table_schema = 'nhr'
                    """
                )
                views = {row[0] for row in cursor.fetchall()}
                missing_views = sorted(EXPECTED_VIEWS - views)
                if missing_views:
                    add(results, "FAIL", "Supabase views", f"missing: {', '.join(missing_views)}")
                else:
                    add(results, "OK", "Supabase views", ", ".join(sorted(EXPECTED_VIEWS)))

                if not missing_tables:
                    cursor.execute("select count(*) from nhr.model_runs")
                    run_count = cursor.fetchone()[0]
                    cursor.execute("select count(*) from nhr.daily_priority_buildings")
                    priority_count = cursor.fetchone()[0]
                    add(results, "OK", "published row counts", f"model_runs={run_count}, daily_priority_buildings={priority_count}")
                    model_run_id = (payload or {}).get("model_run", {}).get("model_run_id")
                    if model_run_id:
                        cursor.execute("select count(*) from nhr.daily_priority_buildings where model_run_id = %s", (model_run_id,))
                        run_priority_count = int(cursor.fetchone()[0])
                        cursor.execute("select count(*) from nhr.prediction_explanations where model_run_id = %s", (model_run_id,))
                        run_explanation_count = int(cursor.fetchone()[0])
                        if run_priority_count == 50 and run_explanation_count == 50:
                            add(results, "OK", "current model_run published", f"{model_run_id}: 50 priority rows, 50 explanation rows")
                        else:
                            add(
                                results,
                                "WARN",
                                "current model_run published",
                                f"{model_run_id}: {run_priority_count} priority rows, {run_explanation_count} explanation rows",
                            )
    except Exception as exc:
        add(results, "FAIL", "database connection", f"{type(exc).__name__}: {exc}")


def summarize(results: list[CheckResult]) -> tuple[str, str]:
    fail_count = sum(result.status == "FAIL" for result in results)
    warn_count = sum(result.status == "WARN" for result in results)
    if fail_count:
        return "NEEDS_FIX", f"{fail_count} fail, {warn_count} warn"
    if warn_count:
        return "READY_WITH_WARNINGS", f"0 fail, {warn_count} warn"
    return "READY", "0 fail, 0 warn"


def write_report(results: list[CheckResult], output: Path, db_url: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    overall, counts = summarize(results)
    lines = [
        "# Supabase Readiness",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"- Overall status: `{overall}`",
        f"- Counts: `{counts}`",
        f"- DB URL: `{mask_db_url(db_url) if db_url else 'not set'}`",
        "",
        "## Checks",
        "",
    ]
    for result in results:
        lines.append(f"- `{result.status}` {result.check}: {result.detail}")
    lines.extend(
        [
            "",
            "## Next Commands",
            "",
            "```bash",
            "make supabase-check",
            "make supabase-publish",
            "```",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Supabase/Postgres reporting readiness before publishing.")
    parser.add_argument("--schema-sql", default=str(DEFAULT_SCHEMA_SQL))
    parser.add_argument("--payload-json", default=str(DEFAULT_PAYLOAD_JSON))
    parser.add_argument("--summary-md", default=str(DEFAULT_SUMMARY_MD))
    parser.add_argument("--output", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--db-url", default=os.environ.get("SUPABASE_DB_URL", ""))
    parser.add_argument("--require-db-url", action="store_true", help="Fail when SUPABASE_DB_URL is not set.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results: list[CheckResult] = []
    payload = validate_local_files(Path(args.schema_sql), Path(args.payload_json), Path(args.summary_md), results)
    if payload is not None:
        validate_payload_shape(payload, results)

    if args.db_url:
        check_database(args.db_url, results, payload)
    elif args.require_db_url:
        add(results, "FAIL", "SUPABASE_DB_URL", "not set")
    else:
        add(results, "WARN", "database connection", "SUPABASE_DB_URL not set; local payload is ready, live DB check skipped")

    output = Path(args.output)
    write_report(results, output, args.db_url)
    overall, counts = summarize(results)
    print(f"supabase readiness written: {output}")
    print(f"overall={overall} counts={counts}")
    if overall == "NEEDS_FIX":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
