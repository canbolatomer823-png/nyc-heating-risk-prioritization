#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
ANALYZER="${NEWS_ANALYZER:-fallback}"
PORT="${NEWS_DASHBOARD_PORT:-18080}"
LOG_DIR="${ROOT_DIR}/logs"
LOCK_DIR="${ROOT_DIR}/tmp/news-dashboard-refresh.lock"

mkdir -p "$LOG_DIR" "${ROOT_DIR}/tmp" "${ROOT_DIR}/outputs"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z') refresh already running" >> "${LOG_DIR}/refresh.log"
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

cd "$ROOT_DIR"

if [ "${NEWS_DASHBOARD_GIT_PULL:-0}" = "1" ]; then
  git pull --ff-only
fi

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python bulunamadı: ${PYTHON_BIN}" >&2
  exit 1
fi

case "$ANALYZER" in
  llm|auto)
    analyzer_args=(--analyzer auto)
    ;;
  fallback)
    analyzer_args=(--analyzer fallback)
    ;;
  *)
    echo "NEWS_ANALYZER fallback, llm veya auto olmalı. Gelen: ${ANALYZER}" >&2
    exit 1
    ;;
esac

{
  echo "== refresh $(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z') =="
  PYTHONPATH=src "$PYTHON_BIN" -m news_pipeline.cli \
    --sources config/sources.json \
    --limit-per-source "${NEWS_LIMIT_PER_SOURCE:-2}" \
    "${analyzer_args[@]}" \
    --output outputs/latest_payloads.jsonl

  PYTHONPATH=src "$PYTHON_BIN" -m news_pipeline.dashboard \
    --payloads outputs/latest_payloads.jsonl \
    --patterns outputs/latest_patterns.json \
    --output outputs/dashboard.html

  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "health=ok port=${PORT}"
  else
    echo "health=not-running port=${PORT}"
  fi
} >> "${LOG_DIR}/refresh.log" 2>&1
