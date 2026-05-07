from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_ROOT.parent

FINAL_WINDOW_NAME = "heat_season_2024_10_01_2025_05_31"
FINAL_WINDOW_ROOT = PROJECT_ROOT / "data" / "windows" / FINAL_WINDOW_NAME
OOT_WINDOW_NAME = "oot_heat_season_2025_10_01_2026_04_26"
OOT_WINDOW_ROOT = PROJECT_ROOT / "data" / "windows" / OOT_WINDOW_NAME

FINAL_RAW_DIR = FINAL_WINDOW_ROOT / "raw"
FINAL_PROCESSED_DIR = FINAL_WINDOW_ROOT / "processed"
FINAL_REPORTS_DIR = FINAL_WINDOW_ROOT / "reports"
FINAL_MODELS_DIR = FINAL_WINDOW_ROOT / "models"
OOT_RAW_DIR = OOT_WINDOW_ROOT / "raw"
OOT_PROCESSED_DIR = OOT_WINDOW_ROOT / "processed"
OOT_REPORTS_DIR = OOT_WINDOW_ROOT / "reports"

FINAL_SPARSE_PANEL_PATH = FINAL_PROCESSED_DIR / "building_day_heat_panel.csv"
FINAL_DENSE_PANEL_PATH = FINAL_PROCESSED_DIR / "building_day_heat_panel_dense.csv"
FINAL_MODELING_TABLE_PATH = FINAL_PROCESSED_DIR / "building_day_modeling_table.csv"
FINAL_SCORED_CSV_PATH = FINAL_PROCESSED_DIR / "logistic_regression_scored.csv"
FINAL_RECORD_LOOKUP_DB_PATH = FINAL_PROCESSED_DIR / "record_lookup.sqlite"
OOT_MODELING_TABLE_PATH = OOT_PROCESSED_DIR / "building_day_modeling_table.csv"
OOT_SCORED_CSV_PATH = OOT_PROCESSED_DIR / "out_of_time_logistic_regression_scored.csv"

FINAL_MODEL_BUNDLE_PATH = FINAL_MODELS_DIR / "logistic_regression_bundle.joblib"
FINAL_MODEL_METADATA_PATH = FINAL_MODELS_DIR / "logistic_regression_bundle.metadata.json"

FINAL_LOGISTIC_METRICS_PATH = FINAL_REPORTS_DIR / "logistic_regression_metrics.md"
FINAL_LOGISTIC_COEFFICIENTS_PATH = FINAL_REPORTS_DIR / "logistic_regression_coefficients.csv"
FINAL_LOGISTIC_RANKING_METRICS_PATH = FINAL_REPORTS_DIR / "logistic_regression_ranking_metrics.csv"
FINAL_STATISTICAL_METRICS_PATH = FINAL_REPORTS_DIR / "statistical_model_metrics.md"
FINAL_STATISTICAL_COEFFICIENTS_PATH = FINAL_REPORTS_DIR / "statistical_model_coefficients.csv"
FINAL_PRIORITY_CSV_PATH = FINAL_REPORTS_DIR / "inspection_priority_latest_day.csv"
FINAL_PRIORITY_SUMMARY_PATH = FINAL_REPORTS_DIR / "inspection_priority_summary.md"
FINAL_PRIORITY_EXPLANATIONS_PATH = FINAL_REPORTS_DIR / "inspection_priority_why_risky.csv"
FINAL_PRIORITY_EXPLANATIONS_SUMMARY_PATH = FINAL_REPORTS_DIR / "inspection_priority_why_risky.md"
FINAL_SEASONAL_ANOVA_REPORT_PATH = FINAL_REPORTS_DIR / "seasonal_anova.md"
FINAL_SEASONAL_ANOVA_TABLE_PATH = FINAL_REPORTS_DIR / "seasonal_anova_daily_metrics.csv"
FINAL_POLICY_SIMULATION_REPORT_PATH = FINAL_REPORTS_DIR / "inspection_policy_simulation.md"
FINAL_POLICY_SIMULATION_TABLE_PATH = FINAL_REPORTS_DIR / "inspection_policy_simulation_daily.csv"
FINAL_POLICY_SIMULATION_SUMMARY_PATH = FINAL_REPORTS_DIR / "inspection_policy_simulation_summary.csv"
FINAL_ERROR_ANALYSIS_REPORT_PATH = FINAL_REPORTS_DIR / "error_analysis.md"
FINAL_ERROR_ANALYSIS_SEGMENTS_PATH = FINAL_REPORTS_DIR / "error_analysis_segments.csv"
FINAL_ERROR_ANALYSIS_TOP_ERRORS_PATH = FINAL_REPORTS_DIR / "error_analysis_top_errors.csv"
FINAL_UNCERTAINTY_REPORT_PATH = FINAL_REPORTS_DIR / "uncertainty_report.md"
FINAL_UNCERTAINTY_TABLE_PATH = FINAL_REPORTS_DIR / "uncertainty_metrics.csv"
FINAL_FAIRNESS_REPORT_PATH = FINAL_REPORTS_DIR / "subgroup_fairness_calibration.md"
FINAL_FAIRNESS_SEGMENTS_PATH = FINAL_REPORTS_DIR / "subgroup_fairness_segments.csv"
FINAL_FAIRNESS_CALIBRATION_PATH = FINAL_REPORTS_DIR / "subgroup_calibration_bins.csv"
FINAL_DRIFT_REPORT_PATH = FINAL_REPORTS_DIR / "train_test_drift_report.md"
FINAL_DRIFT_TABLE_PATH = FINAL_REPORTS_DIR / "train_test_drift_metrics.csv"
FINAL_EXPERIMENT_REGISTRY_PATH = FINAL_REPORTS_DIR / "experiment_registry.csv"
OOT_VALIDATION_REPORT_PATH = OOT_REPORTS_DIR / "out_of_time_validation.md"
OOT_VALIDATION_RANKING_METRICS_PATH = OOT_REPORTS_DIR / "out_of_time_ranking_metrics.csv"
FINAL_PROJECT_AUDIT_PATH = PROJECT_ROOT / "reports" / "final_project_audit.md"

FINAL_PRESENTATION_DECK_PATH = PROJECT_ROOT / "outputs" / "nyc-heating-risk-final" / "output.pptx"
FINAL_BROCHURE_DECK_PATH = PROJECT_ROOT / "outputs" / "nyc-heating-brochure-final" / "output.pptx"
