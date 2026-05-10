#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-projects/nyc-heat-risk/deploy/rendered/k8s}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_RENDERED="$(mktemp)"
trap 'rm -f "$TMP_RENDERED"' EXIT

if [[ -z "${PYTHON_BIN:-}" ]]; then
  for candidate in \
    "$SCRIPT_DIR/../../../.venv/bin/python" \
    "$SCRIPT_DIR/../../.venv/bin/python" \
    "$SCRIPT_DIR/../.venv/bin/python"; do
    if [[ -x "$candidate" ]]; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="python3"
fi

kubectl kustomize "$TARGET_DIR" >"$TMP_RENDERED"
"$PYTHON_BIN" - "$TMP_RENDERED" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

import yaml


path = Path(sys.argv[1])
documents = [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if doc]
if not documents:
    raise SystemExit("No Kubernetes objects were rendered.")

for index, document in enumerate(documents, start=1):
    if not isinstance(document, dict):
        raise SystemExit(f"Rendered document #{index} is not a mapping.")
    kind = document.get("kind")
    api_version = document.get("apiVersion")
    metadata = document.get("metadata")
    if not api_version:
        raise SystemExit(f"Rendered document #{index} is missing apiVersion.")
    if not kind:
        raise SystemExit(f"Rendered document #{index} is missing kind.")
    if not isinstance(metadata, dict) or not metadata.get("name"):
        raise SystemExit(f"Rendered document #{index} ({kind}) is missing metadata.name.")

print(f"validated {len(documents)} rendered Kubernetes objects")
PY
echo "k8s manifests passed local kustomize and YAML checks: $TARGET_DIR"
