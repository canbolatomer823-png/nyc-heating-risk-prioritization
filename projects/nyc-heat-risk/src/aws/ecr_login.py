from __future__ import annotations

import argparse
import base64
from pathlib import Path
import subprocess
import sys

import boto3

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log Docker into ECR using boto3 credentials.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to deploy env file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = load_env_file(Path(args.env_file))
    region = values["AWS_REGION"]
    account_id = values["AWS_ACCOUNT_ID"]
    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"

    session = boto3.session.Session(region_name=region)
    response = session.client("ecr").get_authorization_token(registryIds=[account_id])
    auth = response["authorizationData"][0]
    username, password = base64.b64decode(auth["authorizationToken"]).decode("utf-8").split(":", 1)

    subprocess.run(
        ["docker", "login", "--username", username, "--password-stdin", registry],
        input=password,
        text=True,
        check=True,
    )
    print(f"docker login succeeded for {registry}", flush=True)


if __name__ == "__main__":
    main()
