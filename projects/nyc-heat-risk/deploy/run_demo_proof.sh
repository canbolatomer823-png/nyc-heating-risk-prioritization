#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_FROM_SCRIPT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_ROOT="$(cd "$PROJECT_ROOT_FROM_SCRIPT/../.." && pwd)"

ROOT="${1:-$DEFAULT_ROOT}"
PROJECT_ROOT="$ROOT/projects/nyc-heat-risk"
PYTHON_BIN="$ROOT/.venv/bin/python"
UVICORN_BIN="$ROOT/.venv/bin/uvicorn"
OUT_DIR="${DEMO_OUT_DIR:-$PROJECT_ROOT/reports/demo_proof}"
PORT="${PORT:-$("$PYTHON_BIN" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)}"

FINAL_WINDOW_ROOT="$PROJECT_ROOT/data/windows/heat_season_2024_10_01_2025_05_31"
FINAL_MODEL_BUNDLE="$FINAL_WINDOW_ROOT/models/logistic_regression_bundle.joblib"
FINAL_SCORED_CSV="$FINAL_WINDOW_ROOT/processed/logistic_regression_scored.csv"
FINAL_RECORD_LOOKUP_DB="$FINAL_WINDOW_ROOT/processed/record_lookup.sqlite"
FINAL_PRIORITY_CSV="$FINAL_WINDOW_ROOT/reports/inspection_priority_latest_day.csv"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.json "$OUT_DIR"/*.md "$OUT_DIR"/*.html

if [[ ! -f "$FINAL_MODEL_BUNDLE" || ! -f "$FINAL_SCORED_CSV" ]]; then
  echo "Missing model/scored artifacts. Run: make -C $PROJECT_ROOT train" >&2
  exit 2
fi

if [[ ! -f "$FINAL_PRIORITY_CSV" ]]; then
  "$PYTHON_BIN" "$PROJECT_ROOT/src/reporting/build_inspection_priority_report.py"
fi

if [[ ! -f "$FINAL_RECORD_LOOKUP_DB" ]]; then
  "$PYTHON_BIN" "$PROJECT_ROOT/src/reporting/build_record_lookup_db.py"
fi

export NYC_HEAT_MODEL_BUNDLE="$FINAL_MODEL_BUNDLE"
export NYC_HEAT_SCORED_CSV="$FINAL_SCORED_CSV"
export NYC_HEAT_RECORD_LOOKUP_DB="$FINAL_RECORD_LOOKUP_DB"
export NYC_HEAT_PRIORITY_CSV="$FINAL_PRIORITY_CSV"

cat >"$OUT_DIR/score_payload.json" <<'JSON'
{
  "rows": [
    {
      "building_id": "642725",
      "calendar_date": "2025-05-30",
      "borough": "QUEENS",
      "management_program": "unknown",
      "incident_address": "demo feature row",
      "complaint_count": 4,
      "unique_request_count": 4,
      "no_heat_count": 4,
      "hot_water_problem_count": 0,
      "lag_1_complaints": 3,
      "rolling_3d_complaints": 8,
      "rolling_7d_complaints": 15,
      "rolling_7d_request_count": 15,
      "complaint_day_count_prior": 12,
      "cumulative_complaints_prior": 130,
      "cumulative_request_count_prior": 130,
      "prior_max_daily_complaints": 9,
      "days_since_last_complaint": 1,
      "registration_active_flag": 1,
      "heat_sensor_program_flag": 0,
      "heat_sensor_active_flag": 0,
      "heat_sensor_unit_count": 0,
      "total_linked_violation_count": 0,
      "open_linked_violation_count": 0,
      "unit_count_proxy": 20,
      "weather_avg_temp_c": 0.97,
      "weather_max_temp_c": 6.0,
      "weather_min_temp_c": -3.0,
      "weather_prcp_mm_mean": 0.0,
      "weather_prcp_mm_max": 0.0,
      "weather_wind_mps_mean": 4.0,
      "weather_heating_degree_c": 17.0,
      "weather_freezing_any_flag": 1,
      "weather_temp_drop_c": 4.7,
      "weather_cold_shock_flag": 1,
      "cre_coverage_flag": 1,
      "cre_population": 2500,
      "cre_pred0_pe": 18.0,
      "cre_pred3_pe": 30.0,
      "cre_pred12_pe": 52.0,
      "cre_vulnerability_index": 0.60,
      "cre_high_vulnerability_flag": 1
    }
  ]
}
JSON

cd "$ROOT"

"$UVICORN_BIN" api.app:app \
  --app-dir "$PROJECT_ROOT/src" \
  --host 127.0.0.1 \
  --port "$PORT" >"$OUT_DIR/api.log" 2>&1 &

API_PID=$!
trap 'kill "$API_PID" >/dev/null 2>&1 || true' EXIT

HEALTH_READY=0
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >"$OUT_DIR/health.json.tmp" 2>"$OUT_DIR/health.err"; then
    HEALTH_READY=1
    break
  fi
  sleep 1
done

if [[ "$HEALTH_READY" != "1" ]]; then
  echo "API did not become healthy on port ${PORT}" >&2
  cat "$OUT_DIR/health.err" >&2 2>/dev/null || true
  cat "$OUT_DIR/api.log" >&2 2>/dev/null || true
  exit 7
fi

"$PYTHON_BIN" -m json.tool "$OUT_DIR/health.json.tmp" >"$OUT_DIR/health.json"
rm -f "$OUT_DIR/health.json.tmp"

curl -fsS "http://127.0.0.1:${PORT}/metadata" | "$PYTHON_BIN" -m json.tool >"$OUT_DIR/metadata.json"
curl -fsS "http://127.0.0.1:${PORT}/priorities/latest?top_n=5" | "$PYTHON_BIN" -m json.tool >"$OUT_DIR/priorities_top5.json"
curl -fsS "http://127.0.0.1:${PORT}/dashboard?top_n=5" >"$OUT_DIR/dashboard.html"

"$PYTHON_BIN" - "$OUT_DIR/dashboard.html" "$OUT_DIR/dashboard_status.json" <<'PY'
import json
import sys
from pathlib import Path

html_path = Path(sys.argv[1])
status_path = Path(sys.argv[2])
content = html_path.read_text(encoding="utf-8")
payload = {
    "status": "ok" if "NYC heating complaint risk dashboard" in content else "missing_marker",
    "html_path": str(html_path),
    "bytes": html_path.stat().st_size,
    "contains_priority_table": "Why risky" in content,
}
status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
if payload["status"] != "ok" or not payload["contains_priority_table"]:
    raise SystemExit("dashboard proof failed")
PY

TOP_REF="$("$PYTHON_BIN" - "$OUT_DIR/priorities_top5.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
row = data["rows"][0]
print(f"{row['building_id']}\t{row['calendar_date']}")
PY
)"
IFS=$'\t' read -r TOP_BUILDING_ID TOP_CALENDAR_DATE <<<"$TOP_REF"

curl -fsS "http://127.0.0.1:${PORT}/records/${TOP_BUILDING_ID}?calendar_date=${TOP_CALENDAR_DATE}" \
  | "$PYTHON_BIN" -m json.tool >"$OUT_DIR/record_lookup_top1.json"

curl -fsS -X POST "http://127.0.0.1:${PORT}/score" \
  -H "content-type: application/json" \
  --data @"$OUT_DIR/score_payload.json" \
  | "$PYTHON_BIN" -m json.tool >"$OUT_DIR/score_response.json"

"$PYTHON_BIN" - "$OUT_DIR" "$PROJECT_ROOT" "$PORT" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out_dir = Path(sys.argv[1])
project_root = Path(sys.argv[2])
port = sys.argv[3]

health = json.loads((out_dir / "health.json").read_text(encoding="utf-8"))
metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
priorities = json.loads((out_dir / "priorities_top5.json").read_text(encoding="utf-8"))
dashboard_status = json.loads((out_dir / "dashboard_status.json").read_text(encoding="utf-8"))
record = json.loads((out_dir / "record_lookup_top1.json").read_text(encoding="utf-8"))["row"]
score = json.loads((out_dir / "score_response.json").read_text(encoding="utf-8"))
scored = score["rows"][0]

assert health["status"] == "ok"
assert health["record_lookup_db_loaded"] is True
assert health["scored_csv_readable"] is True
assert health["priority_csv_loaded"] is True
assert metadata["model_type"] == "logistic_regression"
assert len(priorities["rows"]) == 5
assert dashboard_status["status"] == "ok"
assert dashboard_status["contains_priority_table"] is True
assert str(record["building_id"]) == str(priorities["rows"][0]["building_id"])
assert scored["why_risky"]
assert scored["top_positive_contributors"]

top = priorities["rows"][0]
generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

lines = [
    "# Demo Proof Report",
    "",
    f"- Generated at: `{generated_at}`",
    f"- Local API: `http://127.0.0.1:{port}`",
    f"- Artifact source: `{health['artifact_source']['type']}`",
    f"- Model type: `{metadata['model_type']}`",
    f"- Threshold: `{metadata['threshold']}`",
    f"- Scored rows: `{health['scored_row_count']}`",
    f"- Priority rows loaded: `{health['priority_row_count']}`",
    f"- Latest priority date: `{priorities['priority_date']}`",
    "",
    "## What This Proves",
    "",
    "- The FastAPI app can load the trained model bundle, scored CSV, priority CSV, and SQLite lookup artifact.",
    "- The same project artifacts produce a top-N inspection priority list.",
    "- The dashboard endpoint renders an inspector-facing HTML priority view.",
    "- The record lookup endpoint can retrieve a real scored building-day record.",
    "- The score endpoint returns probability, decision threshold, prediction, and a row-level `why_risky` explanation.",
    "",
    "## Top Priority Example",
    "",
    f"- Rank: `{top.get('inspection_priority_rank')}`",
    f"- Building ID: `{top.get('building_id')}`",
    f"- Borough: `{top.get('borough')}`",
    f"- Address: `{top.get('incident_address')}`",
    f"- Probability: `{top.get('model_probability')}`",
    f"- Equity-weighted score: `{top.get('equity_weighted_priority_score')}`",
    f"- Why risky: `{top.get('why_risky', '')}`",
    "",
    "## Score Endpoint Example",
    "",
    f"- Probability: `{scored['probability']}`",
    f"- Threshold: `{scored['threshold']}`",
    f"- Prediction: `{scored['prediction']}`",
    f"- Why risky: `{scored['why_risky']}`",
    "",
    "## Dashboard Proof",
    "",
    f"- Dashboard status: `{dashboard_status['status']}`",
    f"- Dashboard HTML bytes: `{dashboard_status['bytes']}`",
    f"- Dashboard file: `{out_dir / 'dashboard.html'}`",
    "",
    "## Files Created",
    "",
    f"- Health JSON: `{out_dir / 'health.json'}`",
    f"- Metadata JSON: `{out_dir / 'metadata.json'}`",
    f"- Priorities JSON: `{out_dir / 'priorities_top5.json'}`",
    f"- Dashboard HTML: `{out_dir / 'dashboard.html'}`",
    f"- Dashboard status JSON: `{out_dir / 'dashboard_status.json'}`",
    f"- Record lookup JSON: `{out_dir / 'record_lookup_top1.json'}`",
    f"- Score payload JSON: `{out_dir / 'score_payload.json'}`",
    f"- Score response JSON: `{out_dir / 'score_response.json'}`",
    "",
    "## Class Demo Commands",
    "",
    "```bash",
    f"make -C {project_root} demo-proof",
    f"cat {out_dir / 'demo_proof.md'}",
    "```",
    "",
    "Optional live API view:",
    "",
    "```bash",
    f"cat {out_dir / 'priorities_top5.json'}",
    f"cat {out_dir / 'score_response.json'}",
    "```",
]
(out_dir / "demo_proof.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out_dir / "demo_proof.md")
PY

echo "demo proof passed"
