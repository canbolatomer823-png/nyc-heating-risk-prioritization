#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f outputs/dashboard.html ]; then
  echo "outputs/dashboard.html yok. Önce dashboard üret:" >&2
  echo "  make dry-run dashboard" >&2
  exit 1
fi

mkdir -p outputs/server-bundle
bundle="outputs/server-bundle/news-dashboard-server-$(date +%Y%m%d-%H%M%S).tar.gz"

tar -czf "$bundle" \
  outputs/dashboard.html \
  deploy/server/compose.yaml \
  deploy/server/nginx.conf \
  deploy/server/preflight.sh \
  deploy/server/deploy_static.sh \
  deploy/server/nginx-reverse-proxy.example.conf \
  deploy/server/Caddyfile.example \
  DEPLOY_SERVER.md \
  Makefile

echo "$bundle"
