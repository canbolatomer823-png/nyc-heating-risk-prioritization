from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.artifact_store import derive_s3_key, upload_file
from project_paths import (
    FINAL_BROCHURE_DECK_PATH,
    FINAL_DRIFT_REPORT_PATH,
    FINAL_DRIFT_TABLE_PATH,
    FINAL_ERROR_ANALYSIS_REPORT_PATH,
    FINAL_ERROR_ANALYSIS_SEGMENTS_PATH,
    FINAL_ERROR_ANALYSIS_TOP_ERRORS_PATH,
    FINAL_EXPERIMENT_REGISTRY_PATH,
    FINAL_FAIRNESS_CALIBRATION_PATH,
    FINAL_FAIRNESS_REPORT_PATH,
    FINAL_FAIRNESS_SEGMENTS_PATH,
    FINAL_LOGISTIC_METRICS_PATH,
    FINAL_LOGISTIC_RANKING_METRICS_PATH,
    FINAL_MODEL_BUNDLE_PATH,
    FINAL_MODEL_METADATA_PATH,
    FINAL_POLICY_SIMULATION_REPORT_PATH,
    FINAL_POLICY_SIMULATION_SUMMARY_PATH,
    FINAL_POLICY_SIMULATION_TABLE_PATH,
    FINAL_RECORD_LOOKUP_DB_PATH,
    FINAL_PRESENTATION_DECK_PATH,
    FINAL_PRIORITY_CSV_PATH,
    FINAL_PRIORITY_EXPLANATIONS_PATH,
    FINAL_PRIORITY_EXPLANATIONS_SUMMARY_PATH,
    FINAL_PRIORITY_SUMMARY_PATH,
    FINAL_REPORTS_DIR,
    FINAL_SCORED_CSV_PATH,
    FINAL_SEASONAL_ANOVA_REPORT_PATH,
    FINAL_SEASONAL_ANOVA_TABLE_PATH,
    FINAL_STATISTICAL_METRICS_PATH,
    FINAL_UNCERTAINTY_REPORT_PATH,
    FINAL_UNCERTAINTY_TABLE_PATH,
    OOT_VALIDATION_RANKING_METRICS_PATH,
    OOT_VALIDATION_REPORT_PATH,
    PROJECT_ROOT,
)


DEFAULT_ARTIFACTS = [
    (str(FINAL_MODEL_BUNDLE_PATH.relative_to(PROJECT_ROOT)), "models/logistic_regression_bundle.joblib"),
    (str(FINAL_MODEL_METADATA_PATH.relative_to(PROJECT_ROOT)), "models/logistic_regression_bundle.metadata.json"),
    (str(FINAL_RECORD_LOOKUP_DB_PATH.relative_to(PROJECT_ROOT)), "lookup/record_lookup.sqlite"),
    (str(FINAL_SCORED_CSV_PATH.relative_to(PROJECT_ROOT)), "scored/logistic_regression_scored.csv"),
    (str(FINAL_PRIORITY_CSV_PATH.relative_to(PROJECT_ROOT)), "priority/inspection_priority_latest_day.csv"),
    (str(FINAL_PRIORITY_EXPLANATIONS_PATH.relative_to(PROJECT_ROOT)), "priority/inspection_priority_why_risky.csv"),
    (str(FINAL_PRIORITY_SUMMARY_PATH.relative_to(PROJECT_ROOT)), "reports/inspection_priority_summary.md"),
    (str(FINAL_PRIORITY_EXPLANATIONS_SUMMARY_PATH.relative_to(PROJECT_ROOT)), "reports/inspection_priority_why_risky.md"),
    (str(FINAL_LOGISTIC_METRICS_PATH.relative_to(PROJECT_ROOT)), "reports/logistic_regression_metrics.md"),
    (str(FINAL_LOGISTIC_RANKING_METRICS_PATH.relative_to(PROJECT_ROOT)), "reports/logistic_regression_ranking_metrics.csv"),
    (str(FINAL_STATISTICAL_METRICS_PATH.relative_to(PROJECT_ROOT)), "reports/statistical_model_metrics.md"),
    (str(FINAL_SEASONAL_ANOVA_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/seasonal_anova.md"),
    (str(FINAL_SEASONAL_ANOVA_TABLE_PATH.relative_to(PROJECT_ROOT)), "reports/seasonal_anova_daily_metrics.csv"),
    (str(FINAL_POLICY_SIMULATION_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/inspection_policy_simulation.md"),
    (str(FINAL_POLICY_SIMULATION_TABLE_PATH.relative_to(PROJECT_ROOT)), "reports/inspection_policy_simulation_daily.csv"),
    (str(FINAL_POLICY_SIMULATION_SUMMARY_PATH.relative_to(PROJECT_ROOT)), "reports/inspection_policy_simulation_summary.csv"),
    (str(FINAL_FAIRNESS_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/subgroup_fairness_calibration.md"),
    (str(FINAL_FAIRNESS_SEGMENTS_PATH.relative_to(PROJECT_ROOT)), "reports/subgroup_fairness_segments.csv"),
    (str(FINAL_FAIRNESS_CALIBRATION_PATH.relative_to(PROJECT_ROOT)), "reports/subgroup_calibration_bins.csv"),
    (str(FINAL_ERROR_ANALYSIS_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/error_analysis.md"),
    (str(FINAL_ERROR_ANALYSIS_SEGMENTS_PATH.relative_to(PROJECT_ROOT)), "reports/error_analysis_segments.csv"),
    (str(FINAL_ERROR_ANALYSIS_TOP_ERRORS_PATH.relative_to(PROJECT_ROOT)), "reports/error_analysis_top_errors.csv"),
    (str(FINAL_UNCERTAINTY_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/uncertainty_report.md"),
    (str(FINAL_UNCERTAINTY_TABLE_PATH.relative_to(PROJECT_ROOT)), "reports/uncertainty_metrics.csv"),
    (str(FINAL_DRIFT_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/train_test_drift_report.md"),
    (str(FINAL_DRIFT_TABLE_PATH.relative_to(PROJECT_ROOT)), "reports/train_test_drift_metrics.csv"),
    (str(FINAL_EXPERIMENT_REGISTRY_PATH.relative_to(PROJECT_ROOT)), "reports/experiment_registry.csv"),
    (str(OOT_VALIDATION_REPORT_PATH.relative_to(PROJECT_ROOT)), "reports/out_of_time_validation.md"),
    (str(OOT_VALIDATION_RANKING_METRICS_PATH.relative_to(PROJECT_ROOT)), "reports/out_of_time_ranking_metrics.csv"),
    ("data/windows/heat_season_2024_10_01_2025_05_31/reports/heat_data_profile.md", "reports/heat_data_profile.md"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload NYC heat risk artifacts to S3 with a stable prefix.")
    parser.add_argument("--bucket", required=True, help="Destination S3 bucket.")
    parser.add_argument(
        "--prefix",
        default="nyc-heat-risk/latest",
        help="S3 prefix for published artifacts.",
    )
    parser.add_argument(
        "--project-root",
        default=str(PROJECT_ROOT),
        help="Local project root containing models/, data/, and reports/.",
    )
    parser.add_argument(
        "--include-presentation",
        action="store_true",
        help="Also upload the generated class presentation deck.",
    )
    parser.add_argument(
        "--manifest-key",
        default="manifests/latest.json",
        help="Manifest key relative to the prefix.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root)
    artifacts = list(DEFAULT_ARTIFACTS)
    if args.include_presentation:
        artifacts.extend(
            [
                (str(FINAL_PRESENTATION_DECK_PATH.relative_to(PROJECT_ROOT)), "outputs/nyc-heating-risk-final/output.pptx"),
                (str(FINAL_BROCHURE_DECK_PATH.relative_to(PROJECT_ROOT)), "outputs/nyc-heating-brochure-final/output.pptx"),
            ]
        )

    uploads = []
    for relative_local_path, relative_s3_key in artifacts:
        local_path = project_root / relative_local_path
        s3_key = derive_s3_key(args.prefix, relative_s3_key)
        uploads.append(upload_file(local_path, args.bucket, s3_key))
        print(f"uploaded {local_path} -> s3://{args.bucket}/{s3_key}", flush=True)

    manifest = {
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "bucket": args.bucket,
        "prefix": args.prefix,
        "artifacts": uploads,
    }
    manifest_path = FINAL_REPORTS_DIR / "_publish_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest_s3_key = derive_s3_key(args.prefix, args.manifest_key)
    upload_file(manifest_path, args.bucket, manifest_s3_key)
    print(f"uploaded manifest -> s3://{args.bucket}/{manifest_s3_key}", flush=True)


if __name__ == "__main__":
    main()
