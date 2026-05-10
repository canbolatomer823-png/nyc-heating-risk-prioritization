#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
PID_PATH="${LOG_DIR}/statistical_refresh.pid"
LATEST_LOG_PATH="${LOG_DIR}/statistical_refresh.latest.log"

if [[ ! -f "${PID_PATH}" ]]; then
  echo "no statistical refresh pid file"
  exit 1
fi

PID="$(cat "${PID_PATH}")"
if ps -p "${PID}" > /dev/null 2>&1; then
  echo "status=running"
  ps -o pid,etime,%cpu,%mem,command -p "${PID}"
else
  echo "status=not-running"
fi

if [[ -f "${LATEST_LOG_PATH}" ]]; then
  LOG_PATH="$(cat "${LATEST_LOG_PATH}")"
  echo "log=${LOG_PATH}"
  if [[ -f "${LOG_PATH}" ]]; then
    echo "--- log tail ---"
    tail -n 20 "${LOG_PATH}"
  fi
fi
