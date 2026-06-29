#!/usr/bin/env bash
set -Eeuo pipefail

PORT="${NEWS_DASHBOARD_PORT:-18080}"

section() {
  printf '\n== %s ==\n' "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

section "Server"
date -Iseconds 2>/dev/null || date "+%Y-%m-%dT%H:%M:%S%z" || true
hostname || true
id || true
uname -a || true

section "Operating system"
if [ -r /etc/os-release ]; then
  sed -n '1,12p' /etc/os-release
else
  echo "/etc/os-release okunamadı"
fi

section "Disk and memory"
df -h /
free -h 2>/dev/null || true

section "Listening ports"
if command_exists ss; then
  ss -ltnp 2>/dev/null || ss -ltn || true
elif command_exists lsof; then
  lsof -nP -iTCP -sTCP:LISTEN | sed -n '1,80p'
elif command_exists netstat; then
  netstat -ltnp 2>/dev/null || netstat -an | grep LISTEN | sed -n '1,80p' || true
else
  echo "ss/netstat yok; port listesi alınamadı"
fi

section "Target port check"
if command_exists ss && ss -ltn | awk '{print $4}' | grep -Eq "(:|\\.)${PORT}$"; then
  echo "UYARI: ${PORT} portu dolu görünüyor. Farklı NEWS_DASHBOARD_PORT seç."
else
  echo "OK: ${PORT} portu dinlemede görünmüyor."
fi

section "Docker"
if command_exists docker; then
  docker --version || true
  docker compose version || true
  if docker info >/dev/null 2>&1; then
    docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' || true
  else
    echo "Docker CLI var ama daemon erişilemiyor."
  fi
else
  echo "Docker bulunamadı. Kurulum yapmadan önce hocaya/server sahibine sormak daha sağlıklı."
fi

section "Reverse proxy candidates"
for service in nginx apache2 caddy; do
  if command_exists systemctl; then
    systemctl is-active "$service" >/dev/null 2>&1 && echo "$service active" || true
  fi
done

section "Firewall"
if command_exists ufw; then
  ufw status || true
fi
if command_exists firewall-cmd; then
  firewall-cmd --list-all || true
fi

section "Rule"
cat <<'EOF'
Bu script sadece okuma/kontrol yapar.
docker prune, reboot, apt upgrade, servis stop/start veya firewall reset çalıştırmaz.
Deploy sırasında mevcut servis adları, portlar ve reverse proxy configleri ezilmemeli.
EOF
