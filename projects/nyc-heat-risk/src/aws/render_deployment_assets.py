from __future__ import annotations

import argparse
import os
from pathlib import Path


REQUIRED_KEYS = [
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
    parser = argparse.ArgumentParser(description="Render NYC heat risk AWS deployment assets from a single env file.")
    parser.add_argument(
        "--env-file",
        default="projects/nyc-heat-risk/deploy/aws.env",
        help="Path to the deployment env file.",
    )
    parser.add_argument(
        "--project-root",
        default="projects/nyc-heat-risk",
        help="Path to the NYC heat risk project root.",
    )
    parser.add_argument(
        "--output-dir",
        default="projects/nyc-heat-risk/deploy/rendered",
        help="Directory for rendered manifests and SQL.",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing env file: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid env line: {raw_line}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")
    return values


def render_text(template: str, values: dict[str, str]) -> str:
    account = values["AWS_ACCOUNT_ID"]
    region = values["AWS_REGION"]
    repository = values["ECR_REPOSITORY"]
    image_tag = values["IMAGE_TAG"]
    replacements = {
        "REPLACE_WITH_IRSA_ROLE_ARN": values["IRSA_ROLE_ARN"],
        "REPLACE_WITH_ECR/nyc-heat-risk-api:0.1": f"{account}.dkr.ecr.{region}.amazonaws.com/{repository}:{image_tag}",
        "replace-me-artifact-bucket": values["ARTIFACT_BUCKET"],
        "nyc-heat-risk/latest": values["ARTIFACT_PREFIX"],
        "value: us-east-1": f"value: {region}",
        "REPLACE_ME_BUCKET": values["ARTIFACT_BUCKET"],
    }
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def render_file(source: Path, destination: Path, values: dict[str, str]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_text(source.read_text(encoding="utf-8"), values)
    destination.write_text(rendered, encoding="utf-8")


def k8s_manifest_files(project_root: Path) -> list[Path]:
    k8s_root = project_root / "k8s"
    kustomization = k8s_root / "kustomization.yaml"
    manifests = [kustomization]
    lines = kustomization.read_text(encoding="utf-8").splitlines()
    in_resources = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == "resources:":
            in_resources = True
            continue
        if in_resources and raw_line.startswith("  - "):
            manifests.append(k8s_root / stripped[2:].strip())
            continue
        if in_resources and stripped and not raw_line.startswith("  - "):
            in_resources = False
    return manifests


def write_summary(project_root: Path, output_dir: Path, values: dict[str, str]) -> None:
    image_uri = (
        f"{values['AWS_ACCOUNT_ID']}.dkr.ecr.{values['AWS_REGION']}.amazonaws.com/"
        f"{values['ECR_REPOSITORY']}:{values['IMAGE_TAG']}"
    )
    publish_script = project_root / "src" / "aws" / "publish_artifacts.py"
    dockerfile = project_root / "Dockerfile"
    k8s_dir = output_dir / "k8s"
    lines = [
        "# AWS Deploy Values",
        "",
        f"- AWS region: `{values['AWS_REGION']}`",
        f"- AWS account: `{values['AWS_ACCOUNT_ID']}`",
        f"- Artifact bucket: `{values['ARTIFACT_BUCKET']}`",
        f"- Artifact prefix: `{values['ARTIFACT_PREFIX']}`",
        f"- ECR image: `{image_uri}`",
        f"- EKS cluster: `{values['EKS_CLUSTER_NAME']}`",
        f"- IRSA role: `{values['IRSA_ROLE_ARN']}`",
        "",
        "## Next commands",
        "",
        "```bash",
        f"./.venv/bin/python {publish_script} --bucket {values['ARTIFACT_BUCKET']} --prefix {values['ARTIFACT_PREFIX']} --project-root {project_root}",
        f"docker build -f {dockerfile} -t {values['ECR_REPOSITORY']}:{values['IMAGE_TAG']} {project_root}",
        f"docker tag {values['ECR_REPOSITORY']}:{values['IMAGE_TAG']} {image_uri}",
        f"kubectl apply -k {k8s_dir}",
        "```",
    ]
    (output_dir / "deployment-summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    env_values = load_env_file(Path(args.env_file))
    project_root = Path(args.project_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    k8s_output_dir = output_dir / "k8s"
    k8s_output_dir.mkdir(parents=True, exist_ok=True)

    active_manifests = k8s_manifest_files(project_root)
    active_names = {path.name for path in active_manifests}
    for stale_file in k8s_output_dir.glob("*.yaml"):
        if stale_file.name not in active_names:
            stale_file.unlink()

    for yaml_file in active_manifests:
        render_file(yaml_file, k8s_output_dir / yaml_file.name, env_values)

    render_file(
        project_root / "sql" / "04_athena_external_tables.sql",
        output_dir / "sql" / "04_athena_external_tables.sql",
        env_values,
    )

    write_summary(project_root, output_dir, env_values)
    print(f"rendered deployment assets to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
