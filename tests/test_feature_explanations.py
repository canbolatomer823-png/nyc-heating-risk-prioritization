from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.feature_explanations import (
    source_feature_name,
    readable_feature_name,
    raw_value_for,
    build_reason_sentence,
    format_contributor_list,
    is_zero_like,
)
from modeling.risk_features import prepare_feature_frame


class SourceFeatureNameTest(unittest.TestCase):
    def test_numeric_feature(self) -> None:
        source, cat = source_feature_name("num__weather_avg_temp_c")
        self.assertEqual(source, "weather_avg_temp_c")
        self.assertIsNone(cat)

    def test_categorical_feature(self) -> None:
        source, cat = source_feature_name("cat__borough_BRONX")
        self.assertEqual(source, "borough")
        self.assertEqual(cat, "BRONX")

    def test_plain_feature(self) -> None:
        source, cat = source_feature_name("calendar_date")
        self.assertEqual(source, "calendar_date")
        self.assertIsNone(cat)

    def test_unknown_categorical(self) -> None:
        source, cat = source_feature_name("cat__unknown_key_value")
        self.assertIsNotNone(source)


class ReadableFeatureNameTest(unittest.TestCase):
    def test_known_feature(self) -> None:
        self.assertEqual(readable_feature_name("num__complaint_count"), "same-day complaints")

    def test_categorical_with_value(self) -> None:
        self.assertEqual(readable_feature_name("cat__borough_BROOKLYN"), "borough = BROOKLYN")

    def test_unknown_feature_uses_underscore_replacement(self) -> None:
        result = readable_feature_name("num__some_unknown_feature")
        self.assertNotEqual(result, "some_unknown_feature")


class RawValueForTest(unittest.TestCase):
    def test_numeric(self) -> None:
        row = pd.Series({"complaint_count": 5})
        self.assertEqual(raw_value_for(row, "num__complaint_count"), 5)

    def test_categorical(self) -> None:
        row = pd.Series({"borough": "BRONX"})
        self.assertEqual(raw_value_for(row, "cat__borough_BRONX"), "BRONX")

    def test_nan_returns_none(self) -> None:
        row = pd.Series({"complaint_count": np.nan})
        self.assertIsNone(raw_value_for(row, "num__complaint_count"))

    def test_missing_column_returns_none(self) -> None:
        row = pd.Series({})
        self.assertIsNone(raw_value_for(row, "num__missing_col"))


class BuildReasonSentenceTest(unittest.TestCase):
    def test_empty_contributors(self) -> None:
        result = build_reason_sentence([], max_reasons=3)
        self.assertIn("no single positive driver", result)

    def test_fewer_than_max(self) -> None:
        contributors = [
            {"feature": "f1", "label": "complaints", "raw_value": 5, "contribution": 0.5},
            {"feature": "f2", "label": "temperature", "raw_value": -3, "contribution": 0.2},
        ]
        result = build_reason_sentence(contributors, max_reasons=5)
        self.assertIn("complaints=5", result)
        self.assertIn("temperature=-3", result)

    def test_zero_values_skipped(self) -> None:
        contributors = [
            {"feature": "f1", "label": "zero_val", "raw_value": 0, "contribution": 0.5},
            {"feature": "f2", "label": "nonzero", "raw_value": 10, "contribution": 0.3},
        ]
        result = build_reason_sentence(contributors)
        self.assertIn("nonzero=10", result)


class FormatContributorListTest(unittest.TestCase):
    def test_single(self) -> None:
        contributors = [{"feature": "f1", "label": "temp", "raw_value": 15, "contribution": 1.23}]
        result = format_contributor_list(contributors)
        self.assertIn("+1.2300", result)
        self.assertIn("temp=15", result)

    def test_negative_contribution(self) -> None:
        contributors = [{"feature": "f1", "label": "wind", "raw_value": 5, "contribution": -2.5}]
        result = format_contributor_list(contributors)
        self.assertIn("-2.5000", result)


class IsZeroLikeTest(unittest.TestCase):
    def test_actual_zero(self) -> None:
        self.assertTrue(is_zero_like(0))

    def test_very_small(self) -> None:
        self.assertTrue(is_zero_like(1e-15))

    def test_normal_value(self) -> None:
        self.assertFalse(is_zero_like(1.0))

    def test_none(self) -> None:
        self.assertFalse(is_zero_like(None))

    def test_string(self) -> None:
        self.assertTrue(is_zero_like("0"))
        self.assertFalse(is_zero_like("10"))


class PrepareFeatureFrameEdgeCasesTest(unittest.TestCase):
    def test_prepare_feature_frame_with_target(self) -> None:
        dense = pd.DataFrame({
            "calendar_date": pd.date_range("2025-01-01", periods=3),
            "borough": ["BRONX", "BROOKLYN", "MANHATTAN"],
            "management_program": ["PVT", "NYCHA", "PVT"],
            "complaint_count": [0, 1, 2],
            "no_heat_count": [0, 1, 2],
            "hot_water_problem_count": [0, 0, 0],
            "rolling_7d_complaints": [0, 1, 3],
            "rolling_7d_request_count": [0, 1, 3],
            "open_linked_violation_count": [0, 0, 1],
            "unit_count_proxy": [10, 20, 40],
            "heat_sensor_unit_count": [0, 0, 0],
            "days_since_last_complaint": [-1, 1, 10],
            "weather_heating_degree_c": [15, 10, 5],
            "weather_freezing_any_flag": [1, 0, 0],
            "weather_cold_shock_flag": [0, 1, 0],
            "weather_temp_drop_c": [5, 3, 1],
            "cre_vulnerability_index": [0.9, 0.2, 0.8],
            "next_day_complaint_count": [1, 0, 1],
            "weather_avg_temp_c": [-5, 5, 12],
            "weather_max_temp_c": [-2, 8, 15],
            "weather_min_temp_c": [-8, 2, 9],
            "weather_prcp_mm_mean": [0, 1, 0],
            "weather_prcp_mm_max": [0, 2, 0],
            "weather_wind_mps_mean": [3, 4, 2],
            "cumulative_complaints_prior": [0, 5, 15],
            "cumulative_request_count_prior": [0, 5, 15],
            "complaint_day_count_prior": [0, 2, 6],
            "prior_max_daily_complaints": [0, 2, 4],
            "lag_1_complaints": [0, 0, 1],
            "registration_active_flag": [1, 1, 1],
            "heat_sensor_program_flag": [0, 0, 0],
            "heat_sensor_active_flag": [0, 0, 0],
            "total_linked_violation_count": [0, 0, 1],
            "cre_coverage_flag": [1, 1, 1],
            "cre_population": [5000, 3000, 8000],
            "cre_pred0_pe": [10, 5, 15],
            "cre_pred3_pe": [30, 20, 40],
            "cre_pred12_pe": [60, 75, 45],
            "cre_high_vulnerability_flag": [1, 0, 1],
        })
        result = prepare_feature_frame(dense, compute_target=True)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertTrue((result["target"] == [1, 0, 1]).all())

    def test_prepare_feature_frame_empty_df(self) -> None:
        result = prepare_feature_frame(pd.DataFrame(), compute_target=False)
        self.assertIsInstance(result, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
