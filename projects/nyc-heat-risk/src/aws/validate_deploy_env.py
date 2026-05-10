from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import REQUIRED_KEYS, load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate NYC heat risk AWS deployment env values.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to the deployment env file.",
    )
    return parser.parse_args()


def validate(values: dict[str, str]) -> list[str]:
    issues: list[str] = []
    account_id = values.get("AWS_ACCOUNT_ID", "")
    if not re.fullmatch(r"\d{12}", account_id):
        issues.append("AWS_ACCOUNT_ID must be 12 digits.")
    if account_id == "000000000000":
        issues.append("AWS_ACCOUNT_ID is still the sentinel default 000000000000.")

    if values.get("ARTIFACT_BUCKET", "").startswith("replace-me"):
        issues.append("ARTIFACT_BUCKET still contains a placeholder value.")

    irsa_role = values.get("IRSA_ROLE_ARN", "")
    if "000000000000" in irsa_role:
        issues.append("IRSA_ROLE_ARN still points to the sentinel account.")
    if not irsa_role.startswith("arn:aws:iam::"):
        issues.append("IRSA_ROLE_ARN must be a valid IAM role ARN.")

    if values.get("AWS_REGION", "") not in {
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
    }:
        issues.append("AWS_REGION is unusual; confirm the target region is correct.")

    image_tag = values.get("IMAGE_TAG", "")
    if not image_tag or image_tag == "latest":
        issues.append("IMAGE_TAG should be explicit; avoid an empty tag or latest.")

    for key in REQUIRED_KEYS:
        if not values.get(key):
            issues.append(f"{key} is empty.")

    return issues


def main() -> None:
    args = parse_args()
    values = load_env_file(Path(args.env_file))
    issues = validate(values)
    if issues:
        print("deployment env is NOT ready:", flush=True)
        for issue in issues:
            print(f"- {issue}", flush=True)
        raise SystemExit(1)

    print("deployment env is ready", flush=True)


if __name__ == "__main__":
    main()
