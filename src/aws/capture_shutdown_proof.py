from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.render_deployment_assets import load_env_file
from project_paths import PROJECT_ROOT


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "aws_shutdown"
DEFAULT_SUMMARY_JSON = DEFAULT_OUTPUT_DIR / "shutdown_summary.json"
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports" / "aws_shutdown_proof.md"
DEFAULT_LIVE_PROOF_JSON = PROJECT_ROOT / "reports" / "aws_live_deploy" / "proof_summary.json"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def host_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).hostname


def matching_classic_elbs(session: Any, host: str | None) -> list[dict[str, str]]:
    elb = session.client("elb")
    matches: list[dict[str, str]] = []
    paginator = elb.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for item in page.get("LoadBalancerDescriptions", []):
            dns = item.get("DNSName", "")
            name = item.get("LoadBalancerName", "")
            if host and dns == host:
                matches.append({"name": name, "dns": dns})
            elif "nyc-heat-risk" in name:
                matches.append({"name": name, "dns": dns})
    return matches


def matching_elbv2(session: Any, host: str | None) -> list[dict[str, str]]:
    elbv2 = session.client("elbv2")
    matches: list[dict[str, str]] = []
    paginator = elbv2.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for item in page.get("LoadBalancers", []):
            dns = item.get("DNSName", "")
            name = item.get("LoadBalancerName", "")
            if host and dns == host:
                matches.append({"name": name, "dns": dns, "state": item.get("State", {}).get("Code", "")})
            elif "nyc-heat-risk" in name:
                matches.append({"name": name, "dns": dns, "state": item.get("State", {}).get("Code", "")})
    return matches


def tagged_instances(session: Any) -> list[dict[str, str]]:
    ec2 = session.client("ec2")
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Project", "Values": ["nyc-heat-risk"]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )
    instances: list[dict[str, str]] = []
    for reservation in response.get("Reservations", []):
        for item in reservation.get("Instances", []):
            instances.append(
                {
                    "id": item.get("InstanceId", ""),
                    "state": item.get("State", {}).get("Name", ""),
                    "type": item.get("InstanceType", ""),
                }
            )
    return instances


def matching_autoscaling_groups(session: Any, cluster_name: str) -> list[dict[str, Any]]:
    autoscaling = session.client("autoscaling")
    groups: list[dict[str, Any]] = []
    paginator = autoscaling.get_paginator("describe_auto_scaling_groups")
    for page in paginator.paginate():
        for item in page.get("AutoScalingGroups", []):
            name = item.get("AutoScalingGroupName", "")
            tags = {tag.get("Key"): tag.get("Value") for tag in item.get("Tags", [])}
            if cluster_name in name or tags.get("Project") == "nyc-heat-risk":
                groups.append(
                    {
                        "name": name,
                        "desired": item.get("DesiredCapacity"),
                        "instances": len(item.get("Instances", [])),
                    }
                )
    return groups


def capture(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    except ModuleNotFoundError as exc:
        raise SystemExit("Missing AWS Python dependencies. Run with the project virtualenv.") from exc

    env_values = load_env_file(args.env_file)
    region = env_values["AWS_REGION"]
    cluster_name = env_values["EKS_CLUSTER_NAME"]
    session = boto3.session.Session(region_name=region)
    aws_errors = (NoCredentialsError, BotoCoreError, ClientError)
    live_proof = read_json(args.live_proof_json)
    live_host = host_from_url(live_proof.get("base_url"))

    errors: list[str] = []
    checks: dict[str, Any] = {}
    try:
        clusters = session.client("eks").list_clusters().get("clusters", [])
        checks["eks_clusters"] = clusters
        checks["cluster_present"] = cluster_name in clusters
        if checks["cluster_present"]:
            errors.append(f"EKS cluster still exists: {cluster_name}")

        checks["classic_load_balancers"] = matching_classic_elbs(session, live_host)
        if checks["classic_load_balancers"]:
            errors.append("Classic LoadBalancer still exists for project/live proof host")

        checks["elbv2_load_balancers"] = matching_elbv2(session, live_host)
        if checks["elbv2_load_balancers"]:
            errors.append("ELBv2 LoadBalancer still exists for project/live proof host")

        checks["ec2_instances"] = tagged_instances(session)
        if checks["ec2_instances"]:
            errors.append("Tagged EC2 instances still exist")

        checks["autoscaling_groups"] = matching_autoscaling_groups(session, cluster_name)
        if checks["autoscaling_groups"]:
            errors.append("Project AutoScaling Groups still exist")
    except aws_errors as exc:
        errors.append(f"AWS shutdown check failed: {exc}")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "aws_region": region,
        "cluster_name": cluster_name,
        "live_proof_base_url": live_proof.get("base_url"),
        "live_proof_host": live_host,
        "status": "ok" if not errors else "needs_fix",
        "errors": errors,
        "checks": checks,
    }
    write_json(args.summary_json, summary)
    write_report(args.report_md, summary, args.summary_json)
    return summary, errors


def write_report(path: Path, summary: dict[str, Any], summary_json: Path) -> None:
    lines = [
        "# AWS Shutdown Proof",
        "",
        f"- Generated at: `{summary['generated_at_utc']}`",
        f"- Status: `{summary['status']}`",
        f"- Region: `{summary['aws_region']}`",
        f"- EKS cluster name: `{summary['cluster_name']}`",
        f"- Live proof URL checked: `{summary.get('live_proof_base_url')}`",
        f"- Summary JSON: `{summary_json}`",
        "",
        "## Resource Checks",
        "",
        f"- EKS clusters in region: `{summary['checks'].get('eks_clusters', [])}`",
        f"- Matching Classic ELBs: `{summary['checks'].get('classic_load_balancers', [])}`",
        f"- Matching ELBv2 load balancers: `{summary['checks'].get('elbv2_load_balancers', [])}`",
        f"- Tagged EC2 instances: `{summary['checks'].get('ec2_instances', [])}`",
        f"- Matching AutoScaling Groups: `{summary['checks'].get('autoscaling_groups', [])}`",
        "",
    ]
    if summary["errors"]:
        lines.extend(["## Issues", ""])
        lines.extend(f"- {error}" for error in summary["errors"])
        lines.append("")
    else:
        lines.extend(
            [
                "## Interpretation",
                "",
                "- The short-lived EKS demo resources are not present after shutdown.",
                "- S3/ECR/IAM artifacts may remain intentionally because they are reusable and low-cost compared with EKS nodes and load balancers.",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture proof that short-lived AWS/EKS demo resources are shut down.")
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / "deploy" / "aws.env")
    parser.add_argument("--live-proof-json", type=Path, default=DEFAULT_LIVE_PROOF_JSON)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> None:
    summary, errors = capture(parse_args())
    print(f"aws shutdown proof written: {DEFAULT_REPORT_MD}")
    print(f"status={summary['status']} errors={len(errors)}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
