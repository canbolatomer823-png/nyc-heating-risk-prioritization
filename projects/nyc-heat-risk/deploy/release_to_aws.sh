#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE_ROOT/.venv/bin/python}"
ENV_FILE="$PROJECT_ROOT/deploy/aws.env"
RENDERED_DIR="$PROJECT_ROOT/deploy/rendered"
KUBECONFIG_PATH="$PROJECT_ROOT/deploy/generated-kubeconfig.yaml"

DRY_RUN=0
SKIP_BOOTSTRAP=0
SKIP_PUBLISH=0
SKIP_PUSH=0
SKIP_APPLY=0

usage() {
  cat <<'EOF'
Usage: release_to_aws.sh [options]

Options:
  --env-file PATH        Deployment env file. Default: projects/nyc-heat-risk/deploy/aws.env
  --dry-run              Print commands without executing them.
  --skip-bootstrap       Skip boto3 bootstrap of S3/ECR/IRSA.
  --skip-publish         Skip S3 artifact publish.
  --skip-push            Skip Docker build/tag/push and ECR login.
  --skip-apply           Skip kubeconfig generation and kubectl apply.
  --python-bin PATH      Python executable to use. Default: workspace .venv python
  --help                 Show this message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-bootstrap)
      SKIP_BOOTSTRAP=1
      shift
      ;;
    --skip-publish)
      SKIP_PUBLISH=1
      shift
      ;;
    --skip-push)
      SKIP_PUSH=1
      shift
      ;;
    --skip-apply)
      SKIP_APPLY=1
      shift
      ;;
    --python-bin)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" != "1" ]]; then
    "$@"
  fi
}

run_with_env() {
  echo "+ KUBECONFIG=$KUBECONFIG_PATH $*"
  if [[ "$DRY_RUN" != "1" ]]; then
    KUBECONFIG="$KUBECONFIG_PATH" "$@"
  fi
}

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing required command: $name" >&2
    exit 1
  fi
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
  LOCAL_IMAGE_TAG="${ECR_REPOSITORY}:${IMAGE_TAG}"
}

load_env

run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/validate_deploy_env.py" --env-file "$ENV_FILE"

if [[ "$SKIP_BOOTSTRAP" != "1" ]]; then
  run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/bootstrap_stack.py" --env-file "$ENV_FILE" --write-env
  load_env
fi

PREFLIGHT_ARGS=("$PYTHON_BIN" "$PROJECT_ROOT/src/aws/preflight_check.py" "--env-file" "$ENV_FILE")
if [[ "$SKIP_PUSH" != "1" ]]; then
  PREFLIGHT_ARGS+=("--require-docker")
fi
if [[ "$SKIP_APPLY" != "1" ]]; then
  PREFLIGHT_ARGS+=("--require-kubectl")
fi
run "${PREFLIGHT_ARGS[@]}"
run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/render_deployment_assets.py" --env-file "$ENV_FILE" --project-root "$PROJECT_ROOT" --output-dir "$RENDERED_DIR"
run bash "$PROJECT_ROOT/deploy/check_k8s_manifests.sh" "$RENDERED_DIR/k8s"

if [[ "$SKIP_PUBLISH" != "1" ]]; then
  run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/publish_artifacts.py" \
    --bucket "$ARTIFACT_BUCKET" \
    --prefix "$ARTIFACT_PREFIX" \
    --project-root "$PROJECT_ROOT" \
    --include-presentation
fi

if [[ "$SKIP_PUSH" != "1" ]]; then
  if [[ "$DRY_RUN" != "1" ]]; then
    require_cmd docker
  fi
  run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/ecr_login.py" --env-file "$ENV_FILE"
  run docker build -f "$PROJECT_ROOT/Dockerfile" -t "$LOCAL_IMAGE_TAG" "$PROJECT_ROOT"
  run docker tag "$LOCAL_IMAGE_TAG" "$IMAGE_URI"
  run docker push "$IMAGE_URI"
fi

if [[ "$SKIP_APPLY" != "1" ]]; then
  if [[ "$DRY_RUN" != "1" ]]; then
    require_cmd kubectl
  fi
  run "$PYTHON_BIN" "$PROJECT_ROOT/src/aws/write_kubeconfig.py" --env-file "$ENV_FILE" --output "$KUBECONFIG_PATH" --python-bin "$PYTHON_BIN"
  run_with_env kubectl apply -k "$RENDERED_DIR/k8s"
fi

echo "release flow completed"
echo "image_uri=$IMAGE_URI"
