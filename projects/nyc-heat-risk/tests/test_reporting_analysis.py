from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.build_drift_report import build_categorical_rows, build_numeric_rows, downsample
from reporting.build_subgroup_fairness_report import build_report_tables
from reporting.build_uncertainty_report import (
    bootstrap_ranking_rows,
    bootstrap_rows_from_daily,
    daily_classification_metrics,
    selected_inference_intervals,
)
from reporting.simulate_inspection_policies import build_daily_rows, order_policy, summarize_daily_rows


class ReportingAnalysisTest(unittest.TestCase):
    def test_equity_weighted_policy_reorders_by_vulnerability(self) -> None:
        group = pd.DataFrame(
            [
                {
                    "building_id": "A",
                    "model_probability": 0.60,
                    "cre_vulnerability_index": 0.0,
                    "cumulative_complaints_prior": 1,
                    "rolling_7d_complaints": 1,
                    "open_linked_violation_count": 0,
                    "complaint_count": 0,
                },
                {
                    "building_id": "B",
                    "model_probability": 0.50,
                    "cre_vulnerability_index": 0.9,
                    "cumulative_complaints_prior": 0,
                    "rolling_7d_complaints": 0,
                    "open_linked_violation_count": 0,
                    "complaint_count": 0,
                },
            ]
        )
        ordered = order_policy(group, "equity_weighted")
        self.assertEqual(ordered.iloc[0]["building_id"], "B")

    def test_policy_simulation_summary_includes_random_and_deltas(self) -> None:
        scored = pd.DataFrame(
            [
                {
                    "calendar_date": "2025-01-01",
                    "building_id": "1",
                    "target": 1,
                    "model_probability": 0.9,
                    "cumulative_complaints_prior": 10,
                    "rolling_7d_complaints": 5,
                    "open_linked_violation_count": 1,
                    "complaint_count": 2,
                    "heat_sensor_active_flag": 0,
                    "cre_vulnerability_index": 0.9,
                },
                {
                    "calendar_date": "2025-01-01",
                    "building_id": "2",
                    "target": 0,
                    "model_probability": 0.2,
                    "cumulative_complaints_prior": 1,
                    "rolling_7d_complaints": 0,
                    "open_linked_violation_count": 0,
                    "complaint_count": 0,
                    "heat_sensor_active_flag": 0,
                    "cre_vulnerability_index": 0.2,
                },
                {
                    "calendar_date": "2025-01-01",
                    "building_id": "3",
                    "target": 1,
                    "model_probability": 0.8,
                    "cumulative_complaints_prior": 8,
                    "rolling_7d_complaints": 3,
                    "open_linked_violation_count": 1,
                    "complaint_count": 1,
                    "heat_sensor_active_flag": 1,
                    "cre_vulnerability_index": 0.7,
                },
            ]
        )
        rows = build_daily_rows(scored, [2])
        summary = pd.DataFrame(summarize_daily_rows(rows))
        self.assertEqual(set(summary["policy"]), {"model_probability", "equity_weighted", "history_baseline", "random_expectation"})
        logistic_row = summary[summary["policy"] == "model_probability"].iloc[0]
        self.assertIn("delta_hits_vs_random", logistic_row.index)
        self.assertGreaterEqual(float(logistic_row["mean_hits"]), float(summary[summary["policy"] == "random_expectation"].iloc[0]["mean_hits"]))

    def test_fairness_report_tables_cover_borough_and_cre_segments(self) -> None:
        scored = pd.DataFrame(
            [
                {"target": 1, "model_prediction": 1, "model_probability": 0.9, "borough": "BRONX", "management_program": "PVT", "cre_vulnerability_index": 0.9, "cre_coverage_flag": 1},
                {"target": 0, "model_prediction": 0, "model_probability": 0.1, "borough": "BRONX", "management_program": "PVT", "cre_vulnerability_index": 0.8, "cre_coverage_flag": 1},
                {"target": 1, "model_prediction": 0, "model_probability": 0.4, "borough": "MANHATTAN", "management_program": "NYCHA", "cre_vulnerability_index": 0.2, "cre_coverage_flag": 1},
                {"target": 0, "model_prediction": 1, "model_probability": 0.7, "borough": "MANHATTAN", "management_program": "NYCHA", "cre_vulnerability_index": 0.1, "cre_coverage_flag": 1},
                {"target": 1, "model_prediction": 1, "model_probability": 0.8, "borough": "BROOKLYN", "management_program": "PVT", "cre_vulnerability_index": 0.6, "cre_coverage_flag": 1},
                {"target": 0, "model_prediction": 0, "model_probability": 0.2, "borough": "BROOKLYN", "management_program": "PVT", "cre_vulnerability_index": 0.4, "cre_coverage_flag": 1},
            ]
        )
        segments, calibration = build_report_tables(scored, min_group_rows=1, n_bins=3)
        segment_df = pd.DataFrame(segments)
        calibration_df = pd.DataFrame(calibration)
        self.assertIn("overall", set(segment_df["segment_type"]))
        self.assertIn("borough", set(segment_df["segment_type"]))
        self.assertIn("cre_bucket", set(segment_df["segment_type"]))
        self.assertGreater(len(calibration_df), 0)
        self.assertTrue({"low", "mid", "high"}.intersection(set(segment_df[segment_df["segment_type"] == "cre_bucket"]["segment_value"])))

    def test_uncertainty_helpers_produce_intervals_and_selected_inference_rows(self) -> None:
        scored = pd.DataFrame(
            [
                {"calendar_date": "2025-01-01", "target": 1, "model_prediction": 1, "model_probability": 0.8},
                {"calendar_date": "2025-01-01", "target": 0, "model_prediction": 0, "model_probability": 0.2},
                {"calendar_date": "2025-01-02", "target": 1, "model_prediction": 0, "model_probability": 0.4},
                {"calendar_date": "2025-01-02", "target": 0, "model_prediction": 1, "model_probability": 0.7},
            ]
        )
        daily = daily_classification_metrics(scored)
        rows = bootstrap_rows_from_daily(daily, n_boot=50, random_state=7)
        metrics = {row["metric"] for row in rows}
        self.assertIn("f1", metrics)
        self.assertIn("precision", metrics)

        with tempfile.TemporaryDirectory() as tmpdir:
            ranking_path = Path(tmpdir) / "ranking.csv"
            pd.DataFrame(
                [
                    {"k": 10, "precision_at_k": 0.4, "recall_at_k": 0.2, "lift_at_k": 3.0},
                    {"k": 10, "precision_at_k": 0.5, "recall_at_k": 0.3, "lift_at_k": 3.5},
                    {"k": 25, "precision_at_k": 0.3, "recall_at_k": 0.4, "lift_at_k": 2.0},
                    {"k": 25, "precision_at_k": 0.35, "recall_at_k": 0.45, "lift_at_k": 2.3},
                    {"k": 50, "precision_at_k": 0.25, "recall_at_k": 0.5, "lift_at_k": 1.8},
                    {"k": 50, "precision_at_k": 0.28, "recall_at_k": 0.52, "lift_at_k": 1.9},
                ]
            ).to_csv(ranking_path, index=False)

            coeff_path = Path(tmpdir) / "coeff.csv"
            pd.DataFrame(
                [
                    {"model": "gee_logistic", "term": "cre_vulnerability_index", "effect": 3.1, "conf_low": 0.8, "conf_high": 1.4},
                    {"model": "gee_logistic", "term": "weather_temp_drop_c", "effect": 1.1, "conf_low": 0.03, "conf_high": 0.15},
                    {"model": "gee_logistic", "term": "weather_heating_degree_scaled", "effect": 1.4, "conf_low": 0.1, "conf_high": 0.5},
                    {"model": "negative_binomial", "term": "log1p_current_complaint_count", "effect": 3.3, "conf_low": 0.9, "conf_high": 1.5},
                ]
            ).to_csv(coeff_path, index=False)

            ranking_rows = bootstrap_ranking_rows(ranking_path, n_boot=50, random_state=7)
            inference_rows = selected_inference_intervals(coeff_path)

        ranking_groups = {row["metric_group"] for row in ranking_rows}
        inference_metrics = {row["metric"] for row in inference_rows}
        self.assertIn("ranking_k_50", ranking_groups)
        self.assertIn("gee_cre", inference_metrics)
        self.assertIn("gee_temp_drop", inference_metrics)

    def test_drift_helpers_detect_distribution_shift(self) -> None:
        train = pd.DataFrame(
            {
                "weather_heating_degree_c": [10, 11, 9, 10],
                "weather_temp_drop_c": [1, 1, 2, 1],
                "rolling_7d_complaints": [1, 2, 1, 2],
                "cumulative_complaints_prior": [10, 12, 11, 13],
                "open_linked_violation_count": [0, 1, 0, 1],
                "cre_vulnerability_index": [0.2, 0.3, 0.25, 0.35],
                "unit_count_proxy": [10, 11, 12, 13],
                "borough": ["BRONX", "BRONX", "QUEENS", "QUEENS"],
                "management_program": ["PVT", "PVT", "NYCHA", "NYCHA"],
            }
        )
        test = pd.DataFrame(
            {
                "weather_heating_degree_c": [2, 3, 1, 2],
                "weather_temp_drop_c": [5, 6, 5, 4],
                "rolling_7d_complaints": [6, 7, 5, 8],
                "cumulative_complaints_prior": [30, 40, 35, 45],
                "open_linked_violation_count": [2, 2, 3, 3],
                "cre_vulnerability_index": [0.8, 0.85, 0.9, 0.95],
                "unit_count_proxy": [30, 31, 29, 32],
                "borough": ["MANHATTAN", "MANHATTAN", "BRONX", "MANHATTAN"],
                "management_program": ["PVT", "7A", "7A", "7A"],
            }
        )
        numeric_rows = build_numeric_rows(train, test)
        categorical_rows = build_categorical_rows(train, test)
        self.assertTrue(any(float(row["drift_score"]) > 0 for row in numeric_rows))
        self.assertTrue(any(float(row["drift_score"]) > 0 for row in categorical_rows))

        sampled = downsample(pd.concat([train] * 10, ignore_index=True), max_rows=5, random_state=11)
        self.assertEqual(len(sampled), 5)


if __name__ == "__main__":
    unittest.main()
