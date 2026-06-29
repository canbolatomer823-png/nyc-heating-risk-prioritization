#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT="${NEWS_DASHBOARD_PORT:-18080}"
PROJECT="${NEWS_DASHBOARD_PROJECT:-omer-news-dashboard}"
CONTAINER="${NEWS_DASHBOARD_CONTAINER:-omer-news-dashboard}"

cd "$ROOT_DIR"

if [ ! -f outputs/dashboard.html ]; then
  echo "outputs/dashboard.html yok. Önce dashboard üret:" >&2
  echo "  make dry-run dashboard" >&2
  exit 1
fi

if command -v ss >/dev/null 2>&1 && ss -ltn | awk '{print $4}' | grep -Eq "(:|\\.)${PORT}$"; then
  echo "Port ${PORT} dolu görünüyor. Farklı port seç:" >&2
  echo "  NEWS_DASHBOARD_PORT=18081 deploy/server/deploy_static.sh" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker bulunamadı. Mevcut server servislerini bozmamak için otomatik kurulum yapılmadı." >&2
  exit 1
fi

export NEWS_DASHBOARD_PORT="$PORT"
export NEWS_DASHBOARD_CONTAINER="$CONTAINER"

docker compose -p "$PROJECT" -f deploy/server/compose.yaml up -d

printf 'Health check: '
if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "ok"
else
  echo "başarısız" >&2
  docker compose -p "$PROJECT" -f deploy/server/compose.yaml ps
  exit 1
fi

cat <<EOF
Dashboard local server içinde çalışıyor:
  http://127.0.0.1:${PORT}

Not:
  Compose sadece localhost'a bind eder. Dış erişim için mevcut Nginx/Caddy üstünden reverse proxy ekle.
  Container adı: ${CONTAINER}
  Compose project: ${PROJECT}
EOF
