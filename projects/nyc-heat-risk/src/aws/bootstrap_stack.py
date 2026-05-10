from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import boto3
from botocore.exceptions import ClientError

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file


ENV_KEY_ORDER = [
    "AWS_REGION",
    "AWS_ACCOUNT_ID",
    "ARTIFACT_BUCKET",
    "ARTIFACT_PREFIX",
    "ECR_REPOSITORY",
    "EKS_CLUSTER_NAME",
    "IRSA_ROLE_ARN",
    "IMAGE_TAG",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap NYC heat risk AWS resources using boto3.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to deploy env file.",
    )
    parser.add_argument(
        "--namespace",
        default="nyc-heat-risk",
        help="Kubernetes namespace used by the service account.",
    )
    parser.add_argument(
        "--service-account",
        default="nhr-api",
        help="Kubernetes service account name for IRSA.",
    )
    parser.add_argument(
        "--skip-bucket",
        action="store_true",
        help="Skip S3 bucket creation/check.",
    )
    parser.add_argument(
        "--skip-ecr",
        action="store_true",
        help="Skip ECR repository creation/check.",
    )
    parser.add_argument(
        "--skip-irsa",
        action="store_true",
        help="Skip IAM IRSA role creation/update.",
    )
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write discovered account id and IRSA role ARN back into the env file.",
    )
    return parser.parse_args()


def save_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={values[key]}" for key in ENV_KEY_ORDER if key in values]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_bucket(session: boto3.session.Session, bucket: str, region: str) -> None:
    s3 = session.client("s3")
    try:
        s3.head_bucket(Bucket=bucket)
        return
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code not in {"404", "NoSuchBucket", "NotFound", "403"}:
            raise

    params: dict[str, object] = {"Bucket": bucket}
    if region != "us-east-1":
        params["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**params)


def ensure_ecr_repository(session: boto3.session.Session, repository_name: str) -> str:
    ecr = session.client("ecr")
    try:
        response = ecr.describe_repositories(repositoryNames=[repository_name])
        return response["repositories"][0]["repositoryUri"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "RepositoryNotFoundException":
            raise

    response = ecr.create_repository(
        repositoryName=repository_name,
        imageScanningConfiguration={"scanOnPush": True},
        imageTagMutability="MUTABLE",
    )
    return response["repository"]["repositoryUri"]


def describe_cluster_oidc(session: boto3.session.Session, cluster_name: str) -> tuple[str, str]:
    eks = session.client("eks")
    response = eks.describe_cluster(name=cluster_name)
    cluster = response["cluster"]
    issuer = cluster["identity"]["oidc"]["issuer"]
    return cluster["arn"], issuer


def ensure_irsa_role(
    session: boto3.session.Session,
    role_name: str,
    account_id: str,
    issuer_url: str,
    namespace: str,
    service_account: str,
    bucket: str,
    prefix: str,
) -> str:
    iam = session.client("iam")
    provider_path = issuer_url.replace("https://", "")
    provider_arn = f"arn:aws:iam::{account_id}:oidc-provider/{provider_path}"
    subject = f"system:serviceaccount:{namespace}:{service_account}"

    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Federated": provider_arn},
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {
                    "StringEquals": {
                        f"{provider_path}:sub": subject,
                    }
                },
            }
        ],
    }

    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        iam.update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(assume_role_policy))
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="IRSA role for NYC heat risk API and publish job.",
        )["Role"]

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{prefix.strip('/')}/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
                "Condition": {
                    "StringLike": {
                        "s3:prefix": [f"{prefix.strip('/')}/*"],
                    }
                },
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{role_name}-inline",
        PolicyDocument=json.dumps(inline_policy),
    )
    return role["Arn"]


def main() -> None:
    args = parse_args()
    env_path = Path(args.env_file)
    values = load_env_file(env_path)
    region = values["AWS_REGION"]
    session = boto3.session.Session(region_name=region)
    sts = session.client("sts")
    caller = sts.get_caller_identity()
    account_id = caller["Account"]

    values["AWS_ACCOUNT_ID"] = account_id
    print(f"sts identity ok: {caller['Arn']}", flush=True)

    if not args.skip_bucket:
        ensure_bucket(session, values["ARTIFACT_BUCKET"], region)
        print(f"s3 bucket ready: {values['ARTIFACT_BUCKET']}", flush=True)

    if not args.skip_ecr:
        repository_uri = ensure_ecr_repository(session, values["ECR_REPOSITORY"])
        print(f"ecr repository ready: {repository_uri}", flush=True)

    if not args.skip_irsa:
        role_name = values["IRSA_ROLE_ARN"].split("/")[-1]
        _, issuer = describe_cluster_oidc(session, values["EKS_CLUSTER_NAME"])
        irsa_role_arn = ensure_irsa_role(
            session=session,
            role_name=role_name,
            account_id=account_id,
            issuer_url=issuer,
            namespace=args.namespace,
            service_account=args.service_account,
            bucket=values["ARTIFACT_BUCKET"],
            prefix=values["ARTIFACT_PREFIX"],
        )
        values["IRSA_ROLE_ARN"] = irsa_role_arn
        print(f"irsa role ready: {irsa_role_arn}", flush=True)

    if args.write_env:
        save_env_file(env_path, values)
        print(f"updated env file: {env_path}", flush=True)


if __name__ == "__main__":
    main()
