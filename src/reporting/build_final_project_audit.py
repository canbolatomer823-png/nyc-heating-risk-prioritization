from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from project_paths import (
    FINAL_BROCHURE_DECK_PATH,
    FINAL_DRIFT_REPORT_PATH,
    FINAL_ERROR_ANALYSIS_REPORT_PATH,
    FINAL_EXPERIMENT_REGISTRY_PATH,
    FINAL_FAIRNESS_REPORT_PATH,
    FINAL_MODEL_BUNDLE_PATH,
    FINAL_MODEL_METADATA_PATH,
    FINAL_POLICY_SIMULATION_REPORT_PATH,
    FINAL_PRESENTATION_DECK_PATH,
    FINAL_PRIORITY_CSV_PATH,
    FINAL_PRIORITY_EXPLANATIONS_PATH,
    FINAL_PROJECT_AUDIT_PATH,
    FINAL_RECORD_LOOKUP_DB_PATH,
    FINAL_REPORTS_DIR,
    FINAL_SEASONAL_ANOVA_REPORT_PATH,
    FINAL_UNCERTAINTY_REPORT_PATH,
    OOT_VALIDATION_RANKING_METRICS_PATH,
    OOT_VALIDATION_REPORT_PATH,
    PROJECT_ROOT,
)


ROOT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEMO_PROOF_MD = ROOT_REPORTS_DIR / "demo_proof" / "demo_proof.md"
DEMO_PROOF_HEALTH = ROOT_REPORTS_DIR / "demo_proof" / "health.json"
DEMO_PROOF_SCORE = ROOT_REPORTS_DIR / "demo_proof" / "score_response.json"
DEMO_PROOF_DASHBOARD_HTML = ROOT_REPORTS_DIR / "demo_proof" / "dashboard.html"
DEMO_PROOF_DASHBOARD_STATUS = ROOT_REPORTS_DIR / "demo_proof" / "dashboard_status.json"
SUPABASE_SCHEMA_SQL = PROJECT_ROOT / "sql" / "05_supabase_reporting_schema.sql"
SUPABASE_DEMO_SQL = PROJECT_ROOT / "sql" / "06_supabase_demo_queries.sql"
SUPABASE_LIVE_CHECKLIST = PROJECT_ROOT / "deploy" / "SUPABASE_LIVE_CHECKLIST.md"
SUPABASE_ENV = PROJECT_ROOT / "deploy" / "supabase.env"
SUPABASE_PAYLOAD_JSON = FINAL_REPORTS_DIR / "supabase" / "supabase_reporting_payload.json"
SUPABASE_SUMMARY_MD = FINAL_REPORTS_DIR / "supabase" / "supabase_reporting_summary.md"
SUPABASE_PUBLISH_RECEIPT_MD = FINAL_REPORTS_DIR / "supabase" / "supabase_publish_receipt.md"
MODEL_CARD_MD = ROOT_REPORTS_DIR / "model_card.md"
DATA_CARD_MD = ROOT_REPORTS_DIR / "data_card.md"
EVIDENCE_PACK_MD = ROOT_REPORTS_DIR / "evidence_pack" / "README.md"
EVIDENCE_DASHBOARD_PNG = ROOT_REPORTS_DIR / "evidence_pack" / "dashboard_summary.png"
BROCHURE_PDF = PROJECT_ROOT / "outputs" / "nyc-heating-brochure-final" / "output.pdf"
BROCHURE_QR_PNG = PROJECT_ROOT / "outputs" / "nyc-heating-brochure-final" / "brochure_qr.png"
BROCHURE_PRESIGNED_URL_TXT = PROJECT_ROOT / "outputs" / "nyc-heating-brochure-final" / "brochure_presigned_url.txt"
BROCHURE_S3_URI_TXT = PROJECT_ROOT / "outputs" / "nyc-heating-brochure-final" / "brochure_s3_uri.txt"
FINAL_PRESENTATION_QR_DECK = PROJECT_ROOT / "outputs" / "nyc-heating-risk-final" / "output_with_qr.pptx"
FINAL_PRESENTATION_QR_PDF = PROJECT_ROOT / "outputs" / "nyc-heating-risk-final" / "output_with_qr.pdf"
IST312_DOCX = PROJECT_ROOT / "outputs" / "ist312-final-sunumu" / "omer_canbolat_ist312_final_sunumu.docx"
AWS_ENV = PROJECT_ROOT / "deploy" / "aws.env"
AWS_LIVE_DEPLOY_PROOF_MD = ROOT_REPORTS_DIR / "aws_live_deploy_proof.md"
AWS_LIVE_DEPLOY_PROOF_JSON = ROOT_REPORTS_DIR / "aws_live_deploy" / "proof_summary.json"
AWS_SHUTDOWN_PROOF_MD = ROOT_REPORTS_DIR / "aws_shutdown_proof.md"
AWS_SHUTDOWN_PROOF_JSON = ROOT_REPORTS_DIR / "aws_shutdown" / "shutdown_summary.json"


@dataclass
class AuditItem:
    status: str
    area: str
    check: str
    detail: str


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def add(items: list[AuditItem], status: str, area: str, check: str, detail: str) -> None:
    items.append(AuditItem(status=status, area=area, check=check, detail=detail))


def check_file(items: list[AuditItem], path: Path, label: str, min_bytes: int = 1, area: str = "artifacts") -> None:
    if not path.exists():
        add(items, "FAIL", area, label, f"missing: {path}")
        return
    size = path.stat().st_size
    if size < min_bytes:
        add(items, "FAIL", area, label, f"too small: {path} ({size} bytes)")
        return
    add(items, "OK", area, label, f"{path} ({size:,} bytes)")


def parse_s3_presigned_expiry(url: str) -> datetime | None:
    query = parse_qs(urlparse(url).query)
    date_values = query.get("X-Amz-Date") or query.get("x-amz-date")
    expires_values = query.get("X-Amz-Expires") or query.get("x-amz-expires")
    if not date_values or not expires_values:
        return None
    try:
        signed_at = datetime.strptime(date_values[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        expires_seconds = int(expires_values[0])
    except (TypeError, ValueError):
        return None
    return signed_at + timedelta(seconds=expires_seconds)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve_supabase_db_url() -> str:
    return os.environ.get("SUPABASE_DB_URL") or parse_env_file(SUPABASE_ENV).get("SUPABASE_DB_URL", "")


def audit_model(items: list[AuditItem]) -> None:
    check_file(items, FINAL_MODEL_BUNDLE_PATH, "trained model bundle", min_bytes=10_000, area="model")
    check_file(items, FINAL_MODEL_METADATA_PATH, "model metadata", min_bytes=500, area="model")
    if FINAL_MODEL_BUNDLE_PATH.exists():
        try:
            import joblib

            bundle = joblib.load(FINAL_MODEL_BUNDLE_PATH)
            expected_keys = {"model", "metadata"}
            if expected_keys.issubset(bundle):
                add(items, "OK", "model", "model bundle structure", "contains model and metadata")
            else:
                add(items, "FAIL", "model", "model bundle structure", f"missing keys: {sorted(expected_keys - set(bundle))}")
        except Exception as exc:
            add(items, "FAIL", "model", "model bundle load", f"{type(exc).__name__}: {exc}")
    if not FINAL_MODEL_METADATA_PATH.exists():
        return
    metadata = read_json(FINAL_MODEL_METADATA_PATH)
    model_type = metadata.get("model_type")
    threshold = metadata.get("threshold")
    test_metrics = metadata.get("metrics", {}).get("test", {})
    ranking_50 = metadata.get("ranking_metrics", {}).get("50", {})
    if model_type == "logistic_regression":
        add(items, "OK", "model", "primary model type", "logistic_regression")
    else:
        add(items, "FAIL", "model", "primary model type", f"unexpected model_type={model_type!r}")
    if threshold is not None:
        add(items, "OK", "model", "decision threshold", str(threshold))
    else:
        add(items, "FAIL", "model", "decision threshold", "missing")
    if {"f1", "precision", "recall", "roc_auc"}.issubset(test_metrics):
        detail = (
            f"F1={test_metrics['f1']}, precision={test_metrics['precision']}, "
            f"recall={test_metrics['recall']}, AUC={test_metrics['roc_auc']}"
        )
        add(items, "OK", "model", "held-out test metrics", detail)
    else:
        add(items, "FAIL", "model", "held-out test metrics", "missing core metrics")
    if "mean_precision_at_k" in ranking_50:
        add(items, "OK", "model", "Precision@50 metric", str(ranking_50["mean_precision_at_k"]))
    else:
        add(items, "FAIL", "model", "Precision@50 metric", "missing ranking metric k=50")


def audit_priority_outputs(items: list[AuditItem]) -> None:
    check_file(items, FINAL_PRIORITY_CSV_PATH, "priority CSV", min_bytes=1_000, area="priority")
    check_file(items, FINAL_PRIORITY_EXPLANATIONS_PATH, "why_risky CSV", min_bytes=500, area="priority")
    if FINAL_PRIORITY_CSV_PATH.exists():
        rows = count_csv_rows(FINAL_PRIORITY_CSV_PATH)
        status = "OK" if rows == 50 else "WARN"
        add(items, status, "priority", "priority row count", f"{rows} rows")
    if FINAL_PRIORITY_EXPLANATIONS_PATH.exists():
        rows = count_csv_rows(FINAL_PRIORITY_EXPLANATIONS_PATH)
        status = "OK" if rows == 50 else "WARN"
        add(items, status, "priority", "why_risky row count", f"{rows} rows")
    check_file(items, FINAL_RECORD_LOOKUP_DB_PATH, "record lookup sqlite", min_bytes=10_000, area="priority")


def audit_analysis_reports(items: list[AuditItem]) -> None:
    report_paths = [
        (FINAL_SEASONAL_ANOVA_REPORT_PATH, "seasonal ANOVA"),
        (FINAL_POLICY_SIMULATION_REPORT_PATH, "policy simulation"),
        (FINAL_FAIRNESS_REPORT_PATH, "subgroup fairness/calibration"),
        (FINAL_ERROR_ANALYSIS_REPORT_PATH, "error analysis"),
        (FINAL_UNCERTAINTY_REPORT_PATH, "uncertainty report"),
        (FINAL_DRIFT_REPORT_PATH, "drift report"),
        (FINAL_EXPERIMENT_REGISTRY_PATH, "experiment registry"),
        (OOT_VALIDATION_REPORT_PATH, "out-of-time validation"),
        (OOT_VALIDATION_RANKING_METRICS_PATH, "out-of-time ranking metrics"),
    ]
    for path, label in report_paths:
        check_file(items, path, label, min_bytes=100, area="analysis")
    if FINAL_EXPERIMENT_REGISTRY_PATH.exists():
        add(items, "OK", "analysis", "experiment registry rows", f"{count_csv_rows(FINAL_EXPERIMENT_REGISTRY_PATH)} rows")
    if OOT_VALIDATION_RANKING_METRICS_PATH.exists():
        add(items, "OK", "analysis", "OOT ranking rows", f"{count_csv_rows(OOT_VALIDATION_RANKING_METRICS_PATH)} rows")


def audit_demo_and_supabase(items: list[AuditItem]) -> None:
    for path, label in [
        (DEMO_PROOF_MD, "demo proof markdown"),
        (DEMO_PROOF_HEALTH, "demo health JSON"),
        (DEMO_PROOF_SCORE, "demo score JSON"),
        (DEMO_PROOF_DASHBOARD_HTML, "demo dashboard HTML"),
        (DEMO_PROOF_DASHBOARD_STATUS, "demo dashboard status JSON"),
    ]:
        check_file(items, path, label, min_bytes=100, area="demo")
    for path, label in [
        (SUPABASE_SCHEMA_SQL, "optional SQL reporting schema"),
        (SUPABASE_DEMO_SQL, "optional SQL demo query script"),
        (SUPABASE_SUMMARY_MD, "optional SQL reporting summary"),
        (SUPABASE_PAYLOAD_JSON, "optional SQL reporting payload"),
    ]:
        check_file(items, path, label, min_bytes=100, area="demo")
    if SUPABASE_DEMO_SQL.exists():
        sql_text = SUPABASE_DEMO_SQL.read_text(encoding="utf-8")
        required_tokens = [
            "nhr.latest_model_run",
            "nhr.latest_priority_with_explanations",
            "nhr.latest_borough_priority_mix",
            "nhr.demo_proof_events",
        ]
        missing_tokens = [token for token in required_tokens if token not in sql_text]
        if missing_tokens:
            add(items, "FAIL", "demo", "optional SQL query coverage", f"missing: {', '.join(missing_tokens)}")
        else:
            add(items, "OK", "demo", "optional SQL query coverage", "latest run, top priorities, borough mix, and demo events")
    if DEMO_PROOF_DASHBOARD_STATUS.exists():
        dashboard_status = read_json(DEMO_PROOF_DASHBOARD_STATUS)
        if dashboard_status.get("status") == "ok" and dashboard_status.get("contains_priority_table") is True:
            add(items, "OK", "demo", "dashboard proof status", "HTML endpoint rendered priority table")
        else:
            add(items, "FAIL", "demo", "dashboard proof status", str(dashboard_status))
    if SUPABASE_PAYLOAD_JSON.exists():
        payload = read_json(SUPABASE_PAYLOAD_JSON)
        priority_rows = len(payload.get("daily_priority_buildings", []))
        explanation_rows = len(payload.get("prediction_explanations", []))
        demo_events = len(payload.get("demo_proof_events", []))
        if priority_rows == 50 and explanation_rows == 50 and demo_events >= 5:
            add(items, "OK", "demo", "optional SQL payload shape", f"{priority_rows} priority, {explanation_rows} explanations, {demo_events} demo events")
        else:
            add(items, "FAIL", "demo", "optional SQL payload shape", f"{priority_rows} priority, {explanation_rows} explanations, {demo_events} demo events")
    add(items, "OK", "demo", "Supabase live publish", "scoped out; hosted Supabase is not required for the final statistics project")


def audit_portfolio_package(items: list[AuditItem]) -> None:
    for path, label in [
        (MODEL_CARD_MD, "model card"),
        (DATA_CARD_MD, "data card"),
        (EVIDENCE_PACK_MD, "demo evidence pack"),
        (EVIDENCE_DASHBOARD_PNG, "dashboard visual summary"),
    ]:
        min_bytes = 20_000 if path.suffix == ".png" else 500
        check_file(items, path, label, min_bytes=min_bytes, area="portfolio")
    if MODEL_CARD_MD.exists():
        text = MODEL_CARD_MD.read_text(encoding="utf-8")
        if "GLMM is diagnostic only" in text and "ROC AUC" in text:
            add(items, "OK", "portfolio", "model card claim safety", "diagnostic GLMM and primary metrics are explicit")
        else:
            add(items, "FAIL", "portfolio", "model card claim safety", "missing GLMM caveat or core metrics")
    if DATA_CARD_MD.exists():
        text = DATA_CARD_MD.read_text(encoding="utf-8")
        if "Official Data Sources" in text and "Data Risks" in text:
            add(items, "OK", "portfolio", "data card coverage", "sources, feature groups, quality controls, and risks")
        else:
            add(items, "FAIL", "portfolio", "data card coverage", "missing sources or risks")
    if EVIDENCE_PACK_MD.exists():
        text = EVIDENCE_PACK_MD.read_text(encoding="utf-8")
        if (
            "/dashboard" in text
            and "final-audit" in text
            and "dashboard_summary.png" in text
            and "aws_live_deploy_proof.md" in text
            and "aws_shutdown_proof.md" in text
        ):
            add(items, "OK", "portfolio", "evidence pack run order", "dashboard, visual summary, API proof, AWS proof, and audit")
        else:
            add(items, "FAIL", "portfolio", "evidence pack run order", "missing demo run order")


def audit_presentation(items: list[AuditItem]) -> None:
    check_file(items, FINAL_PRESENTATION_DECK_PATH, "final presentation PPTX", min_bytes=20_000, area="presentation")
    check_file(items, FINAL_PRESENTATION_QR_DECK, "final presentation QR PPTX", min_bytes=20_000, area="presentation")
    check_file(items, FINAL_PRESENTATION_QR_PDF, "final presentation QR PDF", min_bytes=20_000, area="presentation")
    check_file(items, FINAL_BROCHURE_DECK_PATH, "brochure PPTX", min_bytes=20_000, area="presentation")
    check_file(items, BROCHURE_PDF, "brochure PDF", min_bytes=20_000, area="presentation")
    check_file(items, BROCHURE_QR_PNG, "brochure QR PNG", min_bytes=5_000, area="presentation")
    check_file(items, BROCHURE_S3_URI_TXT, "brochure S3 URI", min_bytes=20, area="presentation")
    check_file(items, BROCHURE_PRESIGNED_URL_TXT, "brochure QR presigned URL", min_bytes=100, area="presentation")
    if BROCHURE_PRESIGNED_URL_TXT.exists():
        expiry = parse_s3_presigned_expiry(BROCHURE_PRESIGNED_URL_TXT.read_text(encoding="utf-8").strip())
        if expiry is None:
            add(items, "WARN", "presentation", "brochure QR expiry", "could not parse presigned URL expiry")
        else:
            now = datetime.now(timezone.utc)
            if expiry <= now:
                add(items, "FAIL", "presentation", "brochure QR expiry", f"expired at {expiry.isoformat()}")
            elif expiry - now < timedelta(hours=24):
                add(items, "WARN", "presentation", "brochure QR expiry", f"expires soon at {expiry.isoformat()}")
            else:
                add(items, "OK", "presentation", "brochure QR expiry", f"valid until {expiry.isoformat()}")
    check_file(items, IST312_DOCX, "IST312 topic form DOCX", min_bytes=10_000, area="presentation")


def audit_aws(items: list[AuditItem]) -> None:
    check_file(items, AWS_ENV, "AWS env file", min_bytes=50, area="aws")
    env_values = parse_env_file(AWS_ENV)
    if env_values.get("AWS_ACCOUNT_ID") == "000000000000":
        add(items, "WARN", "aws", "AWS account id", "placeholder remains; expected until paid/live deploy day")
    else:
        add(items, "OK", "aws", "AWS account id", env_values.get("AWS_ACCOUNT_ID", "missing"))
    if "000000000000" in env_values.get("IRSA_ROLE_ARN", ""):
        add(items, "WARN", "aws", "IRSA role ARN", "placeholder remains; expected until live AWS setup")
    else:
        add(items, "OK", "aws", "IRSA role ARN", env_values.get("IRSA_ROLE_ARN", "missing"))
    credentials = Path.home() / ".aws" / "credentials"
    config = Path.home() / ".aws" / "config"
    add(items, "OK" if credentials.exists() else "WARN", "aws", "AWS credentials", str(credentials) if credentials.exists() else "missing until live deploy")
    add(items, "OK" if config.exists() else "WARN", "aws", "AWS config", str(config) if config.exists() else "missing until live deploy")
    docker_path = shutil.which("docker")
    add(items, "OK" if docker_path else "WARN", "aws", "docker CLI", docker_path or "missing")
    if docker_path:
        try:
            completed = subprocess.run(
                [docker_path, "version", "--format", "{{.Server.Version}}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if completed.returncode == 0:
                add(items, "OK", "aws", "docker daemon", completed.stdout.strip() or "reachable")
            else:
                detail = (completed.stderr or completed.stdout or "daemon not reachable").strip()
                add(items, "WARN", "aws", "docker daemon", detail)
        except Exception as exc:
            add(items, "WARN", "aws", "docker daemon", f"{type(exc).__name__}: {exc}")
    add(items, "OK" if shutil.which("kubectl") else "WARN", "aws", "kubectl", shutil.which("kubectl") or "missing")
    if AWS_LIVE_DEPLOY_PROOF_JSON.exists():
        proof = read_json(AWS_LIVE_DEPLOY_PROOF_JSON)
        if proof.get("status") == "ok" and proof.get("remote_url") is True and proof.get("artifact_source_type") == "s3":
            add(items, "OK", "aws", "AWS live deploy proof", f"captured timestamped live proof: {AWS_LIVE_DEPLOY_PROOF_MD}")
        else:
            add(items, "WARN", "aws", "AWS live deploy proof", f"incomplete proof: {proof}")
    else:
        add(items, "WARN", "aws", "AWS live deploy proof", "not captured yet; run `make aws-live-proof BASE_URL=...` after release")
    if AWS_SHUTDOWN_PROOF_JSON.exists():
        proof = read_json(AWS_SHUTDOWN_PROOF_JSON)
        if proof.get("status") == "ok":
            add(items, "OK", "aws", "AWS shutdown proof", f"short-lived EKS resources absent after demo: {AWS_SHUTDOWN_PROOF_MD}")
        else:
            add(items, "WARN", "aws", "AWS shutdown proof", f"incomplete shutdown proof: {proof}")
    elif AWS_LIVE_DEPLOY_PROOF_JSON.exists():
        add(items, "WARN", "aws", "AWS shutdown proof", "live proof exists but shutdown proof is missing; run `make aws-shutdown-proof` after deleting EKS/LB resources")


def audit_claim_scan(items: list[AuditItem]) -> None:
    scan_paths = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "DEMO_PROOF_GUIDE.md",
        PROJECT_ROOT / "SUPABASE_REPORTING_GUIDE.md",
        Path("<workspace-root>/docs/nyc-heat-risk-final-rehearsal-pack.md"),
        Path("<workspace-root>/docs/nyc-heat-risk-slide-script.md"),
        Path("<workspace-root>/docs/nyc-heat-risk-slide-script-prova.md"),
    ]
    risky_patterns = ["AWS deploy tamam", "GLMM ana modelim", "production-ready"]
    findings: list[str] = []
    for path in scan_paths:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            if "deme" in lowered or "do not" in lowered or "avoid" in lowered:
                continue
            for pattern in risky_patterns:
                if pattern.lower() in lowered:
                    findings.append(f"{path}:{line_no}: {line.strip()}")
    if findings:
        add(items, "WARN", "claims", "risky wording scan", " | ".join(findings[:5]))
    else:
        add(items, "OK", "claims", "risky wording scan", "no unsafe positive claims found in main docs")


def summarize(items: list[AuditItem]) -> tuple[str, str]:
    fail_count = sum(item.status == "FAIL" for item in items)
    warn_count = sum(item.status == "WARN" for item in items)
    if fail_count:
        return "NEEDS_FIX", f"{fail_count} fail, {warn_count} warn"
    if warn_count:
        return "READY_WITH_KNOWN_BLOCKERS", f"0 fail, {warn_count} warn"
    return "READY", "0 fail, 0 warn"


def write_report(items: list[AuditItem], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    overall, counts = summarize(items)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Final Project Audit",
        "",
        f"- Generated at: `{now}`",
        f"- Overall status: `{overall}`",
        f"- Counts: `{counts}`",
        "",
        "## Interpretation",
        "",
        "- `OK`: ready or verified locally.",
        "- `WARN`: intentional remaining live integration or non-blocking caveat.",
        "- `FAIL`: must fix before presenting as complete.",
        "",
    ]
    for area in ["model", "priority", "analysis", "demo", "portfolio", "presentation", "aws", "claims"]:
        area_items = [item for item in items if item.area == area]
        if not area_items:
            continue
        lines.extend([f"## {area.title()}", ""])
        for item in area_items:
            lines.append(f"- `{item.status}` {item.check}: {item.detail}")
        lines.append("")
    lines.extend(
        [
            "## Short Answer",
            "",
            "- Core analytics, local API proof, presentation, brochure, QR access, and AWS proof are audit-ready if there are no `FAIL` rows above.",
            "- Hosted Supabase is intentionally scoped out; optional local SQL payloads remain as an appendix only.",
            "- AWS is complete as a timestamped cloud proof only when live endpoint proof and shutdown proof both pass.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a final audit report for the NYC heat-risk project.")
    parser.add_argument("--output", default=str(FINAL_PROJECT_AUDIT_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    items: list[AuditItem] = []
    audit_model(items)
    audit_priority_outputs(items)
    audit_analysis_reports(items)
    audit_demo_and_supabase(items)
    audit_portfolio_package(items)
    audit_presentation(items)
    audit_aws(items)
    audit_claim_scan(items)
    output = Path(args.output)
    write_report(items, output)
    overall, counts = summarize(items)
    print(f"final audit written: {output}")
    print(f"overall={overall} counts={counts}")
    if overall == "NEEDS_FIX":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
