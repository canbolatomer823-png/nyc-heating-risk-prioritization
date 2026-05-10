#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

ENV_FILE="${1:-$PROJECT_ROOT/deploy/aws.env}"
OUTPUT_DIR="${2:-$PROJECT_ROOT/deploy/rendered}"

"$PYTHON_BIN" "$PROJECT_ROOT/src/aws/validate_deploy_env.py" \
  --env-file "$ENV_FILE"

"$PYTHON_BIN" "$PROJECT_ROOT/src/aws/render_deployment_assets.py" \
  --env-file "$ENV_FILE" \
  --project-root "$PROJECT_ROOT" \
  --output-dir "$OUTPUT_DIR"

echo "deploy assets are ready under $OUTPUT_DIR"
