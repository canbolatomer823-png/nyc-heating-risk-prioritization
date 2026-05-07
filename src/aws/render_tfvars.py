from __future__ import annotations

import argparse
from pathlib import Path
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render terraform.tfvars from deploy/aws.env values.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to deploy env file.",
    )
    parser.add_argument(
        "--output",
        default="projects/nyc-heat-risk/infra/terraform/terraform.tfvars",
        help="Rendered terraform.tfvars output path.",
    )
    parser.add_argument(
        "--cluster-oidc-provider-arn",
        default='arn:aws:iam::000000000000:oidc-provider/REPLACE_ME',
        help="OIDC provider ARN for the target EKS cluster.",
    )
    parser.add_argument(
        "--cluster-oidc-issuer-url",
        default="https://REPLACE_ME",
        help="OIDC issuer URL for the target EKS cluster.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    values = load_env_file(Path(args.env_file))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    role_name = values["IRSA_ROLE_ARN"].split("/")[-1]
    lines = [
        f'region = "{values["AWS_REGION"]}"',
        f'artifact_bucket = "{values["ARTIFACT_BUCKET"]}"',
        f'artifact_prefix = "{values["ARTIFACT_PREFIX"]}"',
        f'ecr_repository = "{values["ECR_REPOSITORY"]}"',
        f'irsa_role_name = "{role_name}"',
        f'cluster_oidc_provider_arn = "{args.cluster_oidc_provider_arn}"',
        f'cluster_oidc_issuer_url = "{args.cluster_oidc_issuer_url}"',
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote terraform tfvars to {output_path}", flush=True)


if __name__ == "__main__":
    main()
