#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"
PYTHON_BIN="$WORKSPACE_ROOT/.venv/bin/python"
OUT_PATH="$PROJECT_ROOT/reports/class_demo_check.md"
DOWNLOADS_DIR="${DOWNLOADS_DIR:-$HOME/Downloads}"

BROCHURE_PDF="$PROJECT_ROOT/outputs/nyc-heating-brochure-final/output.pdf"
BROCHURE_QR_URL="$PROJECT_ROOT/outputs/nyc-heating-brochure-final/brochure_presigned_url.txt"
FINAL_PRESENTATION_QR_PDF="$PROJECT_ROOT/outputs/nyc-heating-risk-final/output_with_qr.pdf"
FINAL_PRESENTATION_QR_PPTX="$PROJECT_ROOT/outputs/nyc-heating-risk-final/output_with_qr.pptx"
FINAL_AUDIT="$PROJECT_ROOT/reports/final_project_audit.md"
DEMO_PROOF="$PROJECT_ROOT/reports/demo_proof/demo_proof.md"
EKAMPUS_ZIP="$DOWNLOADS_DIR/NYC_Heating_Risk_Ekampus_Teslim_Omer_Canbolat_22050622.zip"

mkdir -p "$(dirname "$OUT_PATH")"

status_rows=()

add_row() {
  local status="$1"
  local check="$2"
  local detail="$3"
  status_rows+=("| ${status} | ${check} | ${detail} |")
}

file_check() {
  local path="$1"
  local label="$2"
  local min_bytes="$3"
  if [[ ! -f "$path" ]]; then
    add_row "FAIL" "$label" "missing: \`$path\`"
    return
  fi
  local size
  size="$(wc -c <"$path" | tr -d ' ')"
  if (( size < min_bytes )); then
    add_row "FAIL" "$label" "too small: ${size} bytes"
    return
  fi
  add_row "OK" "$label" "${size} bytes"
}

run_make() {
  local target="$1"
  local log_path="$PROJECT_ROOT/reports/class_demo_${target}.log"
  if make -C "$PROJECT_ROOT" "$target" >"$log_path" 2>&1; then
    add_row "OK" "make ${target}" "passed; log: \`$log_path\`"
  else
    add_row "FAIL" "make ${target}" "failed; log: \`$log_path\`"
  fi
}

run_make demo-proof
run_make final-audit

file_check "$DEMO_PROOF" "demo proof report" 1000
file_check "$FINAL_AUDIT" "final audit report" 3000
file_check "$FINAL_PRESENTATION_QR_PDF" "QR presentation PDF" 20000
file_check "$FINAL_PRESENTATION_QR_PPTX" "QR presentation PPTX" 20000
file_check "$BROCHURE_PDF" "brochure PDF" 20000
file_check "$EKAMPUS_ZIP" "e-kampus zip" 100000

if command -v docker >/dev/null 2>&1; then
  if docker_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null)"; then
    add_row "OK" "Docker daemon" "reachable: ${docker_version}"
  else
    add_row "WARN" "Docker daemon" "Docker Desktop is not reachable; open Docker Desktop before Docker/AWS demo"
  fi
else
  add_row "WARN" "Docker CLI" "docker command not found"
fi

if [[ -f "$BROCHURE_QR_URL" ]]; then
  qr_url="$(cat "$BROCHURE_QR_URL")"
  qr_tmp="$(mktemp)"
  http_code="$(curl -s -L --max-time 20 -o "$qr_tmp" -w '%{http_code}' "$qr_url" || true)"
  if [[ "$http_code" == "200" ]]; then
    remote_size="$(wc -c <"$qr_tmp" | tr -d ' ')"
    local_size="$(wc -c <"$BROCHURE_PDF" | tr -d ' ')"
    if [[ "$remote_size" == "$local_size" ]]; then
      add_row "OK" "brochure QR link" "GET 200; remote size matches local PDF (${remote_size} bytes)"
    else
      add_row "WARN" "brochure QR link" "GET 200 but size differs: remote=${remote_size}, local=${local_size}"
    fi
  else
    add_row "FAIL" "brochure QR link" "HTTP ${http_code}; regenerate or refresh QR/S3 link"
  fi
  rm -f "$qr_tmp"
else
  add_row "FAIL" "brochure QR URL" "missing: \`$BROCHURE_QR_URL\`"
fi

if ! curl -fsS --max-time 3 "http://127.0.0.1:8000/health" >"$PROJECT_ROOT/reports/class_demo_local_health.json" 2>/dev/null; then
  nohup make -C "$PROJECT_ROOT" serve >"$PROJECT_ROOT/reports/class_demo_local_serve.log" 2>&1 &
  for _ in {1..20}; do
    if curl -fsS --max-time 3 "http://127.0.0.1:8000/health" >"$PROJECT_ROOT/reports/class_demo_local_health.json" 2>/dev/null; then
      break
    fi
    sleep 1
  done
fi

if curl -fsS --max-time 5 "http://127.0.0.1:8000/health" >"$PROJECT_ROOT/reports/class_demo_local_health.json" 2>/dev/null; then
  health_status="$("$PYTHON_BIN" - <<'PY'
import json
from pathlib import Path
path = Path("<project-root>/reports/class_demo_local_health.json")
data = json.loads(path.read_text())
print(data.get("status", "unknown"))
PY
)"
  add_row "OK" "live local dashboard server" "127.0.0.1:8000 /health status=${health_status}"
else
  add_row "WARN" "live local dashboard server" "not running on 127.0.0.1:8000; start with \`make -C $PROJECT_ROOT serve\`"
fi

overall="READY"
for row in "${status_rows[@]}"; do
  if [[ "$row" == \|*\ FAIL\ * ]]; then
    overall="NEEDS_FIX"
    break
  fi
  if [[ "$row" == \|*\ WARN\ * && "$overall" != "NEEDS_FIX" ]]; then
    overall="READY_WITH_NOTES"
  fi
done

{
  echo "# Class Demo Check"
  echo
  echo "- Generated at: \`$(date -u '+%Y-%m-%d %H:%M:%S UTC')\`"
  echo "- Overall: \`${overall}\`"
  echo
  echo "| Status | Check | Detail |"
  echo "|---|---|---|"
  printf '%s\n' "${status_rows[@]}"
  echo
  echo "## Demo Order"
  echo
  echo "1. Open the QR presentation PDF."
  echo "2. Show the QR slide and let classmates open the brochure."
  echo "3. Run \`make -C $PROJECT_ROOT demo-proof\`."
  echo "4. If you want the browser dashboard, run \`make -C $PROJECT_ROOT serve\` and open \`http://127.0.0.1:8000/dashboard?top_n=10\`."
  echo "5. Show \`reports/final_project_audit.md\`: it should say \`READY\`, \`0 fail, 0 warn\`."
  echo
  echo "## Cost Safety"
  echo
  echo "This check does not create EKS, EC2, LoadBalancer, or other paid AWS runtime resources. It only reads local files, checks Docker, calls the local API if running, and validates the existing brochure QR link."
} >"$OUT_PATH"

cat "$OUT_PATH"

if [[ "$overall" == "NEEDS_FIX" ]]; then
  exit 1
fi
