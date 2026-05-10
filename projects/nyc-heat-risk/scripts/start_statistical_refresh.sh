#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(cd "${PROJECT_DIR}/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${WORKSPACE_ROOT}/.venv/bin/python}"
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_PATH="${LOG_DIR}/statistical_refresh_${TIMESTAMP}.log"
PID_PATH="${LOG_DIR}/statistical_refresh.pid"
LATEST_LOG_PATH="${LOG_DIR}/statistical_refresh.latest.log"

printf 'starting %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "${LOG_PATH}"

nohup env PYTHONUNBUFFERED=1 "${PYTHON_BIN}" "${PROJECT_DIR}/src/modeling/statistical_models.py" \
  >>"${LOG_PATH}" 2>&1 < /dev/null &

PID="$!"
printf '%s\n' "${PID}" > "${PID_PATH}"
printf '%s\n' "${LOG_PATH}" > "${LATEST_LOG_PATH}"

echo "started statistical refresh"
echo "pid=${PID}"
echo "log=${LOG_PATH}"
