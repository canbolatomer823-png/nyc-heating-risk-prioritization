from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AWS preflight checks for the heat risk deployment.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to deploy env file.",
    )
    parser.add_argument(
        "--require-docker",
        action="store_true",
        help="Fail if docker is missing or the daemon is not reachable.",
    )
    parser.add_argument(
        "--require-kubectl",
        action="store_true",
        help="Fail if kubectl is missing.",
    )
    return parser.parse_args()


def check_sts(session: Any, expected_account: str, aws_errors: tuple[type[BaseException], ...]) -> tuple[bool, str]:
    try:
        identity = session.client("sts").get_caller_identity()
        actual_account = identity["Account"]
        if actual_account != expected_account:
            return False, f"STS account mismatch: env={expected_account}, caller={actual_account}, arn={identity['Arn']}"
        return True, f"STS ok: account={actual_account}, arn={identity['Arn']}"
    except aws_errors as exc:
        return False, f"STS failed: {exc}"


def check_bucket(session: Any, bucket: str, expected_region: str, aws_errors: tuple[type[BaseException], ...]) -> tuple[bool, str]:
    try:
        s3 = session.client("s3")
        s3.head_bucket(Bucket=bucket)
        location = s3.get_bucket_location(Bucket=bucket).get("LocationConstraint") or "us-east-1"
        if location != expected_region:
            return False, f"S3 bucket region mismatch for {bucket}: env={expected_region}, actual={location}"
        return True, f"S3 bucket ok: {bucket} (region={location})"
    except aws_errors as exc:
        return False, f"S3 bucket check failed for {bucket}: {exc}"


def check_ecr(
    session: Any,
    repository: str,
    expected_account: str,
    expected_region: str,
    aws_errors: tuple[type[BaseException], ...],
) -> tuple[bool, str]:
    try:
        response = session.client("ecr").describe_repositories(repositoryNames=[repository])
        repo = response["repositories"][0]
        registry_id = repo["registryId"]
        repository_uri = repo["repositoryUri"]
        if registry_id != expected_account:
            return False, f"ECR registry mismatch for {repository}: env={expected_account}, actual={registry_id}"
        if f".{expected_region}.amazonaws.com/" not in repository_uri:
            return False, f"ECR region mismatch in repository URI for {repository}: {repository_uri}"
        return True, f"ECR repo ok: {repository_uri}"
    except aws_errors as exc:
        return False, f"ECR repository check failed for {repository}: {exc}"


def check_eks_cluster(
    session: Any,
    cluster_name: str,
    expected_account: str,
    expected_region: str,
    aws_errors: tuple[type[BaseException], ...],
) -> tuple[bool, str]:
    try:
        cluster = session.client("eks").describe_cluster(name=cluster_name)["cluster"]
        status = cluster["status"]
        cluster_arn = cluster["arn"]
        if status != "ACTIVE":
            return False, f"EKS cluster is not ACTIVE: name={cluster_name}, status={status}"
        if f":{expected_account}:cluster/" not in cluster_arn:
            return False, f"EKS cluster account mismatch: env={expected_account}, arn={cluster_arn}"
        if f".{expected_region}.eks.amazonaws.com" not in cluster["endpoint"]:
            return False, f"EKS cluster region mismatch: env={expected_region}, endpoint={cluster['endpoint']}"
        return True, f"EKS cluster ok: name={cluster_name}, status={status}"
    except aws_errors as exc:
        return False, f"EKS cluster check failed for {cluster_name}: {exc}"


def check_irsa_role(
    session: Any,
    role_arn: str,
    bucket: str,
    prefix: str,
    aws_errors: tuple[type[BaseException], ...],
) -> tuple[bool, str]:
    try:
        iam = session.client("iam")
        role_name = role_arn.split("/")[-1]
        role = iam.get_role(RoleName=role_name)["Role"]
        actual_arn = role["Arn"]
        if actual_arn != role_arn:
            return False, f"IRSA role ARN mismatch: env={role_arn}, actual={actual_arn}"

        assume_doc = role.get("AssumeRolePolicyDocument", {})
        statements = assume_doc.get("Statement", [])
        has_web_identity = any(stmt.get("Action") == "sts:AssumeRoleWithWebIdentity" for stmt in statements)
        if not has_web_identity:
            return False, f"IRSA role missing sts:AssumeRoleWithWebIdentity trust: {role_name}"

        inline_names = iam.list_role_policies(RoleName=role_name).get("PolicyNames", [])
        if not inline_names:
            return False, f"IRSA role has no inline policies: {role_name}"

        policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=inline_names[0])["PolicyDocument"]
        policy_text = str(policy_doc)
        expected_s3_arn = f"arn:aws:s3:::{bucket}/{prefix.strip('/')}/*"
        if expected_s3_arn not in policy_text:
            return False, f"IRSA inline policy does not include expected artifact prefix: {expected_s3_arn}"

        return True, f"IRSA role ok: {role_name}"
    except aws_errors as exc:
        return False, f"IRSA role check failed for {role_arn}: {exc}"


def check_local_command(name: str, invocation: list[str]) -> tuple[bool, str]:
    if shutil.which(name) is None:
        return False, f"Local command missing: {name}"
    try:
        completed = subprocess.run(invocation, check=True, capture_output=True, text=True)
        snippet = (completed.stdout or completed.stderr).strip().splitlines()
        preview = snippet[0] if snippet else "ok"
        return True, f"{name} ok: {preview}"
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or exc.stderr or "").strip()
        return False, f"{name} check failed: {output or exc}"


def main() -> None:
    args = parse_args()
    values = load_env_file(Path(args.env_file))
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing AWS Python dependencies. Run this script with the project virtualenv, "
            "for example `./.venv/bin/python projects/nyc-heat-risk/src/aws/preflight_check.py ...`."
        ) from exc

    aws_errors = (NoCredentialsError, BotoCoreError, ClientError)
    session = boto3.session.Session(region_name=values["AWS_REGION"])

    checks = [
        check_sts(session, values["AWS_ACCOUNT_ID"], aws_errors),
        check_bucket(session, values["ARTIFACT_BUCKET"], values["AWS_REGION"], aws_errors),
        check_ecr(session, values["ECR_REPOSITORY"], values["AWS_ACCOUNT_ID"], values["AWS_REGION"], aws_errors),
        check_eks_cluster(session, values["EKS_CLUSTER_NAME"], values["AWS_ACCOUNT_ID"], values["AWS_REGION"], aws_errors),
        check_irsa_role(session, values["IRSA_ROLE_ARN"], values["ARTIFACT_BUCKET"], values["ARTIFACT_PREFIX"], aws_errors),
    ]
    if args.require_docker:
        checks.append(check_local_command("docker", ["docker", "info", "--format", "{{.ServerVersion}}"]))
    if args.require_kubectl:
        checks.append(check_local_command("kubectl", ["kubectl", "version", "--client=true", "--output=yaml"]))

    failed = False
    for ok, message in checks:
        print(message, flush=True)
        if not ok:
            failed = True

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
