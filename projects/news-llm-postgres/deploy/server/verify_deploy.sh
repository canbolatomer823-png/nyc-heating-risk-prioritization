#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${NEWS_DASHBOARD_PORT:-18080}"
PROJECT="${NEWS_DASHBOARD_PROJECT:-omer-news-dashboard}"
PROOF_PATH="${ROOT_DIR}/outputs/deploy-proof.json"

cd "$ROOT_DIR"
mkdir -p outputs

health_status="fail"
index_status="fail"
container_status="unknown"

if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  health_status="ok"
fi

if curl -fsSI "http://127.0.0.1:${PORT}/" | grep -q "200"; then
  index_status="ok"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  container_status="$(docker compose -p "$PROJECT" -f deploy/server/compose.yaml ps --format json 2>/dev/null | tr '\n' ' ' | sed 's/"/\\"/g')"
fi

python3 - "$PROOF_PATH" "$PORT" "$health_status" "$index_status" "$container_status" <<'PY'
from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

proof_path = Path(sys.argv[1])
port = sys.argv[2]
health_status = sys.argv[3]
index_status = sys.argv[4]
container_status = sys.argv[5]

payload = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "host": socket.gethostname(),
    "local_url": f"http://127.0.0.1:{port}/",
    "health_url": f"http://127.0.0.1:{port}/health",
    "health_status": health_status,
    "index_status": index_status,
    "container_status": container_status,
}
proof_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

if [ "$health_status" != "ok" ] || [ "$index_status" != "ok" ]; then
  echo "Deploy doğrulaması başarısız. Proof: ${PROOF_PATH}" >&2
  exit 1
fi

echo "Proof yazıldı: ${PROOF_PATH}"
