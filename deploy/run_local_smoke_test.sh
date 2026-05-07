#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_FROM_SCRIPT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_ROOT="$(cd "$PROJECT_ROOT_FROM_SCRIPT/../.." && pwd)"

ROOT="${1:-$DEFAULT_ROOT}"
PROJECT_ROOT="$ROOT/projects/nyc-heat-risk"
PORT="${PORT:-$("$ROOT/.venv/bin/python" - <<'PY'
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

cd "$ROOT"

if [[ "${SMOKE_RETRAIN:-0}" == "1" || ! -f "$FINAL_MODEL_BUNDLE" || ! -f "$FINAL_SCORED_CSV" ]]; then
  ./.venv/bin/python "$PROJECT_ROOT/src/modeling/logistic_regression_model.py" >/tmp/nhr-train.log
fi

if [[ ! -f "$FINAL_RECORD_LOOKUP_DB" ]]; then
  ./.venv/bin/python "$PROJECT_ROOT/src/reporting/build_record_lookup_db.py" >/tmp/nhr-record-lookup.log
fi

export NYC_HEAT_MODEL_BUNDLE="$FINAL_MODEL_BUNDLE"
export NYC_HEAT_SCORED_CSV="$FINAL_SCORED_CSV"
export NYC_HEAT_RECORD_LOOKUP_DB="$FINAL_RECORD_LOOKUP_DB"

./.venv/bin/uvicorn api.app:app \
  --app-dir "$PROJECT_ROOT/src" \
  --host 127.0.0.1 \
  --port "$PORT" >/tmp/nhr-api.log 2>&1 &

API_PID=$!
trap 'kill $API_PID >/dev/null 2>&1 || true' EXIT

HEALTH_JSON=""
for _ in $(seq 1 30); do
  if HEALTH_JSON=$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/tmp/nhr-health.err); then
    break
  fi
  sleep 1
done

if [[ -z "$HEALTH_JSON" ]]; then
  echo "API did not become healthy on port ${PORT}" >&2
  cat /tmp/nhr-health.err >&2 2>/dev/null || true
  cat /tmp/nhr-api.log >&2 2>/dev/null || true
  exit 7
fi

METADATA_JSON=$(curl -fsS "http://127.0.0.1:${PORT}/metadata")
PRIORITY_JSON=$(curl -fsS "http://127.0.0.1:${PORT}/priorities/latest?top_n=3")
SCORE_JSON=$(curl -fsS -X POST "http://127.0.0.1:${PORT}/score" \
  -H 'content-type: application/json' \
  -d '{"rows":[{"building_id":"642725","borough":"QUEENS","management_program":"unknown","complaint_count":4,"unique_request_count":4,"no_heat_count":4,"hot_water_problem_count":0,"lag_1_complaints":3,"rolling_3d_complaints":8,"rolling_7d_complaints":15,"rolling_7d_request_count":15,"complaint_day_count_prior":12,"cumulative_complaints_prior":130,"cumulative_request_count_prior":130,"prior_max_daily_complaints":9,"days_since_last_complaint":1,"registration_active_flag":1,"heat_sensor_program_flag":0,"heat_sensor_active_flag":0,"heat_sensor_unit_count":0,"total_linked_violation_count":0,"open_linked_violation_count":0,"unit_count_proxy":20,"weather_avg_temp_c":0.97,"weather_max_temp_c":6.0,"weather_min_temp_c":-3.0,"weather_prcp_mm_mean":0.0,"weather_prcp_mm_max":0.0,"weather_wind_mps_mean":4.0,"weather_heating_degree_c":17.0,"weather_freezing_any_flag":1,"weather_temp_drop_c":4.7,"weather_cold_shock_flag":1}]}')

python3 - <<'PY' "$HEALTH_JSON" "$METADATA_JSON" "$PRIORITY_JSON" "$SCORE_JSON"
import json
import sys

health = json.loads(sys.argv[1])
metadata = json.loads(sys.argv[2])
priorities = json.loads(sys.argv[3])
score = json.loads(sys.argv[4])

assert health["status"] == "ok"
assert metadata["model_type"] == "logistic_regression"
assert abs(float(health["threshold"]) - float(metadata["threshold"])) < 1e-9
assert health["record_lookup_db_loaded"] is True
assert health["scored_csv_present"] is True
assert health["scored_csv_readable"] is True
assert health["scored_row_count"] > 0
assert priorities["top_n"] == 3
assert len(priorities["rows"]) == 3
assert len(score["rows"]) == 1
scored = score["rows"][0]
assert "probability" in scored
assert scored["why_risky"]
assert scored["top_positive_contributors"]

print("local smoke test passed")
PY
