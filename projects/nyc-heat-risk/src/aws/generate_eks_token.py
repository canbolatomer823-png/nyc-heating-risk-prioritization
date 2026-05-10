from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json

import boto3
from botocore.signers import RequestSigner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an EKS authentication token using boto3 credentials.")
    parser.add_argument("--cluster-name", required=True, help="EKS cluster name.")
    parser.add_argument("--region", required=True, help="AWS region.")
    parser.add_argument(
        "--exec-credential",
        action="store_true",
        help="Print Kubernetes ExecCredential JSON instead of just the token.",
    )
    return parser.parse_args()


def build_token(cluster_name: str, region: str) -> tuple[str, str]:
    session = boto3.session.Session(region_name=region)
    sts_client = session.client("sts")
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError("AWS credentials are not available for EKS token generation.")

    signer = RequestSigner(
        sts_client.meta.service_model.service_id,
        region,
        "sts",
        "v4",
        credentials,
        session.events,
    )
    presigned_url = signer.generate_presigned_url(
        request_dict={
            "method": "GET",
            "url": "https://sts.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
            "body": {},
            "headers": {"x-k8s-aws-id": cluster_name},
            "context": {},
        },
        region_name=region,
        expires_in=60,
        operation_name="",
    )
    token = "k8s-aws-v1." + base64.urlsafe_b64encode(presigned_url.encode("utf-8")).decode("utf-8").rstrip("=")
    expiration = (datetime.now(timezone.utc) + timedelta(minutes=14)).isoformat()
    return token, expiration


def main() -> None:
    args = parse_args()
    token, expiration = build_token(args.cluster_name, args.region)
    if args.exec_credential:
        payload = {
            "apiVersion": "client.authentication.k8s.io/v1beta1",
            "kind": "ExecCredential",
            "status": {
                "expirationTimestamp": expiration,
                "token": token,
            },
        }
        print(json.dumps(payload), flush=True)
        return
    print(token, flush=True)


if __name__ == "__main__":
    main()
