#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"
ENV_FILE="${1:-$PROJECT_ROOT/deploy/aws.env}"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE_ROOT/.venv/bin/python}"

status_ok() {
  printf '[OK] %s\n' "$1"
}

status_warn() {
  printf '[WARN] %s\n' "$1"
}

status_fail() {
  printf '[FAIL] %s\n' "$1"
}

print_header() {
  printf '\n%s\n' "$1"
}

print_header "Local deploy readiness"

if [[ -f "$ENV_FILE" ]]; then
  status_ok "env file present: $ENV_FILE"
else
  status_fail "env file missing: $ENV_FILE"
fi

if [[ -f "$HOME/.aws/credentials" ]]; then
  status_ok "~/.aws/credentials present"
else
  status_warn "~/.aws/credentials missing"
fi

if [[ -f "$HOME/.aws/config" ]]; then
  status_ok "~/.aws/config present"
else
  status_warn "~/.aws/config missing"
fi

if command -v docker >/dev/null 2>&1; then
  if docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    status_ok "docker daemon reachable"
  else
    status_fail "docker installed but daemon is not reachable"
  fi
else
  status_fail "docker is not installed"
fi

if command -v kubectl >/dev/null 2>&1; then
  status_ok "kubectl installed"
else
  status_fail "kubectl is not installed"
fi

if command -v aws >/dev/null 2>&1; then
  status_ok "aws CLI installed"
else
  status_warn "aws CLI not installed (acceptable for this repo's boto3-based release flow)"
fi

if [[ -x "$PYTHON_BIN" ]]; then
  status_ok "python available: $PYTHON_BIN"
else
  status_fail "python not executable: $PYTHON_BIN"
fi

print_header "Env validation"
if "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/validate_deploy_env.py" --env-file "$ENV_FILE"; then
  status_ok "deploy env passes validation"
else
  status_fail "deploy env still has unresolved values"
fi

print_header "Next actions if anything failed"
printf '1. Open Docker Desktop if docker daemon is unreachable.\n'
printf '2. Fill real AWS values in %s.\n' "$ENV_FILE"
printf '3. Add local AWS credentials under ~/.aws/credentials and ~/.aws/config.\n'
printf '4. Then run:\n'
printf '   make -C %s aws-bootstrap\n' "$PROJECT_ROOT"
printf '   make -C %s aws-preflight-release\n' "$PROJECT_ROOT"
printf '   make -C %s release-dry-run\n' "$PROJECT_ROOT"
