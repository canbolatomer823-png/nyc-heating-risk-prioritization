#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_ROOT/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$WORKSPACE_ROOT/.venv/bin/python}"
ENV_FILE="$PROJECT_ROOT/deploy/aws.env"

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=""
ARTIFACT_BUCKET=""
ARTIFACT_PREFIX="nyc-heat-risk/latest"
ECR_REPOSITORY="nyc-heat-risk-api"
EKS_CLUSTER_NAME="nyc-heat-risk"
IRSA_ROLE_NAME="nyc-heat-risk-irsa"
IRSA_ROLE_ARN=""
IMAGE_TAG="0.1"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: configure_aws_env.sh --account-id 123456789012 [options]

Writes deploy/aws.env with non-secret AWS deployment values.
This script does NOT write AWS access keys.

Required:
  --account-id ID          12-digit AWS account id

Options:
  --region REGION          Default: us-east-1
  --bucket NAME            Default: omer-nyc-heat-risk-ACCOUNT-REGION
  --prefix PREFIX          Default: nyc-heat-risk/latest
  --ecr-repository NAME    Default: nyc-heat-risk-api
  --eks-cluster NAME       Default: nyc-heat-risk
  --irsa-role-name NAME    Default: nyc-heat-risk-irsa
  --irsa-role-arn ARN      Overrides --irsa-role-name
  --image-tag TAG          Default: 0.1
  --env-file PATH          Default: deploy/aws.env
  --dry-run                Print env file content without writing
  --help                   Show this help

Example:
  bash deploy/configure_aws_env.sh \
    --account-id 123456789012 \
    --region us-east-1 \
    --bucket omer-nyc-heat-risk-123456789012-us-east-1 \
    --eks-cluster nyc-heat-risk
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id)
      AWS_ACCOUNT_ID="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --bucket)
      ARTIFACT_BUCKET="$2"
      shift 2
      ;;
    --prefix)
      ARTIFACT_PREFIX="$2"
      shift 2
      ;;
    --ecr-repository)
      ECR_REPOSITORY="$2"
      shift 2
      ;;
    --eks-cluster)
      EKS_CLUSTER_NAME="$2"
      shift 2
      ;;
    --irsa-role-name)
      IRSA_ROLE_NAME="$2"
      shift 2
      ;;
    --irsa-role-arn)
      IRSA_ROLE_ARN="$2"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
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

if [[ ! "$AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
  echo "AWS account id must be 12 digits. Got: ${AWS_ACCOUNT_ID:-<empty>}" >&2
  exit 2
fi

if [[ -z "$ARTIFACT_BUCKET" ]]; then
  ARTIFACT_BUCKET="omer-nyc-heat-risk-${AWS_ACCOUNT_ID}-${AWS_REGION}"
fi

if [[ -z "$IRSA_ROLE_ARN" ]]; then
  IRSA_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${IRSA_ROLE_NAME}"
fi

ENV_CONTENT="$(cat <<EOF
AWS_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
ARTIFACT_BUCKET=${ARTIFACT_BUCKET}
ARTIFACT_PREFIX=${ARTIFACT_PREFIX}
ECR_REPOSITORY=${ECR_REPOSITORY}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME}
IRSA_ROLE_ARN=${IRSA_ROLE_ARN}
IMAGE_TAG=${IMAGE_TAG}
EOF
)"

if [[ "$DRY_RUN" == "1" ]]; then
  printf '%s\n' "$ENV_CONTENT"
  exit 0
fi

mkdir -p "$(dirname "$ENV_FILE")"
tmp_file="${ENV_FILE}.tmp"
printf '%s\n' "$ENV_CONTENT" >"$tmp_file"
mv "$tmp_file" "$ENV_FILE"

"$PYTHON_BIN" "$PROJECT_ROOT/src/aws/validate_deploy_env.py" --env-file "$ENV_FILE"
printf 'wrote %s\n' "$ENV_FILE"
