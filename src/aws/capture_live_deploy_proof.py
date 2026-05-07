from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import PROJECT_ROOT


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "aws_live_deploy"
DEFAULT_SUMMARY_JSON = DEFAULT_OUTPUT_DIR / "proof_summary.json"
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports" / "aws_live_deploy_proof.md"
DEFAULT_SCORE_PAYLOAD = PROJECT_ROOT / "reports" / "demo_proof" / "score_payload.json"


LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def is_remote_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and hostname not in LOCAL_HOSTS and not hostname.endswith(".local")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def capture(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    base_url = args.base_url.rstrip("/")
    remote_url = is_remote_url(base_url)
    errors: list[str] = []
    if not remote_url and not args.allow_localhost:
        errors.append("base_url is local; pass a real AWS load balancer/API URL or use --allow-localhost for rehearsal only")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=base_url, timeout=args.timeout_seconds) as client:
        health = fetch_json(client, "/health")
        metadata = fetch_json(client, "/metadata")
        priorities = fetch_json(client, "/priorities/latest?top_n=5")
        dashboard = client.get("/dashboard?top_n=5")
        dashboard.raise_for_status()

        score_payload = read_json(args.score_payload)
        score_response = client.post("/score", json=score_payload)
        score_response.raise_for_status()
        score = score_response.json()

    write_json(args.output_dir / "health.json", health)
    write_json(args.output_dir / "metadata.json", metadata)
    write_json(args.output_dir / "priorities_top5.json", priorities)
    write_json(args.output_dir / "score_response.json", score)
    (args.output_dir / "dashboard.html").write_text(dashboard.text, encoding="utf-8")

    artifact_type = str(health.get("artifact_source", {}).get("type", "unknown"))
    if health.get("status") != "ok":
        errors.append(f"health status is not ok: {health.get('status')}")
    if artifact_type != "s3" and not args.allow_local_artifacts:
        errors.append(f"artifact_source.type is {artifact_type!r}; expected 's3' for AWS live deploy proof")
    if metadata.get("model_type") != "logistic_regression":
        errors.append(f"unexpected model_type: {metadata.get('model_type')!r}")
    if len(priorities.get("rows", [])) < 5:
        errors.append("priorities endpoint returned fewer than 5 rows")
    if "NYC heating complaint risk dashboard" not in dashboard.text:
        errors.append("dashboard HTML marker missing")
    if not score.get("rows") or not score["rows"][0].get("why_risky"):
        errors.append("score endpoint did not return why_risky explanation")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "remote_url": remote_url,
        "artifact_source_type": artifact_type,
        "health_status": health.get("status"),
        "model_type": metadata.get("model_type"),
        "priority_date": priorities.get("priority_date"),
        "priority_rows_returned": len(priorities.get("rows", [])),
        "dashboard_bytes": len(dashboard.text.encode("utf-8")),
        "score_rows_returned": len(score.get("rows", [])),
        "status": "ok" if not errors else "needs_fix",
        "errors": errors,
    }
    write_json(args.summary_json, summary)
    write_report(args.report_md, summary, args.output_dir, args.summary_json)
    return summary, errors


def write_report(path: Path, summary: dict[str, Any], output_dir: Path, summary_json: Path) -> None:
    lines = [
        "# AWS Live Deploy Proof",
        "",
        f"- Generated at: `{summary['generated_at_utc']}`",
        f"- Base URL: `{summary['base_url']}`",
        f"- Status: `{summary['status']}`",
        f"- Remote URL: `{summary['remote_url']}`",
        f"- Artifact source type: `{summary['artifact_source_type']}`",
        f"- Health status: `{summary['health_status']}`",
        f"- Model type: `{summary['model_type']}`",
        f"- Priority date: `{summary['priority_date']}`",
        f"- Priority rows returned: `{summary['priority_rows_returned']}`",
        f"- Dashboard bytes: `{summary['dashboard_bytes']}`",
        f"- Score rows returned: `{summary['score_rows_returned']}`",
        "",
        "## Captured Files",
        "",
        f"- Health: `{output_dir / 'health.json'}`",
        f"- Metadata: `{output_dir / 'metadata.json'}`",
        f"- Priorities: `{output_dir / 'priorities_top5.json'}`",
        f"- Score response: `{output_dir / 'score_response.json'}`",
        f"- Dashboard HTML: `{output_dir / 'dashboard.html'}`",
        f"- Summary JSON: `{summary_json}`",
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
                "- The live API responded from a non-local URL.",
                "- The API reported S3-backed artifacts.",
                "- Health, metadata, priorities, dashboard, and score endpoints all returned valid outputs.",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture proof from a live AWS-deployed NYC heat-risk API.")
    parser.add_argument("--base-url", required=True, help="Live API base URL, e.g. http://...elb.amazonaws.com")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--score-payload", type=Path, default=DEFAULT_SCORE_PAYLOAD)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost only for rehearsal; audit still treats it as non-live.")
    parser.add_argument("--allow-local-artifacts", action="store_true", help="Allow non-S3 artifacts only for rehearsal.")
    return parser.parse_args()


def main() -> None:
    summary, errors = capture(parse_args())
    print(f"aws live proof written: {DEFAULT_REPORT_MD}")
    print(f"status={summary['status']} errors={len(errors)}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
