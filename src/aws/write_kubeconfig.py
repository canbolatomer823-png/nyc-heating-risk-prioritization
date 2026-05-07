from __future__ import annotations

import argparse
from pathlib import Path
import sys

import boto3

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a kubeconfig for the NYC heat risk EKS cluster.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to deploy env file.",
    )
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/deploy/generated-kubeconfig.yaml",
        help="Output kubeconfig path.",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python executable that kubectl should use for token generation.",
    )
    return parser.parse_args()


def build_kubeconfig(cluster_name: str, region: str, endpoint: str, certificate_data: str, python_bin: str) -> str:
    token_script = Path(__file__).resolve().parent / "generate_eks_token.py"
    return f"""apiVersion: v1
kind: Config
clusters:
- name: {cluster_name}
  cluster:
    server: {endpoint}
    certificate-authority-data: {certificate_data}
contexts:
- name: {cluster_name}
  context:
    cluster: {cluster_name}
    user: {cluster_name}
current-context: {cluster_name}
users:
- name: {cluster_name}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: {python_bin}
      args:
      - {token_script}
      - --cluster-name
      - {cluster_name}
      - --region
      - {region}
      - --exec-credential
"""


def main() -> None:
    args = parse_args()
    values = load_env_file(Path(args.env_file))
    region = values["AWS_REGION"]
    cluster_name = values["EKS_CLUSTER_NAME"]

    session = boto3.session.Session(region_name=region)
    cluster = session.client("eks").describe_cluster(name=cluster_name)["cluster"]
    kubeconfig = build_kubeconfig(
        cluster_name=cluster_name,
        region=region,
        endpoint=cluster["endpoint"],
        certificate_data=cluster["certificateAuthority"]["data"],
        python_bin=args.python_bin,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(kubeconfig, encoding="utf-8")
    print(f"wrote kubeconfig to {output_path}", flush=True)


if __name__ == "__main__":
    main()
