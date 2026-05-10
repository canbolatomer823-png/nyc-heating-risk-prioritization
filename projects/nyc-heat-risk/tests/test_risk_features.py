from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modeling.risk_features import prepare_feature_frame


class PrepareFeatureFrameTest(unittest.TestCase):
    def test_prepare_feature_frame_builds_expected_derived_columns(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "calendar_date": "2025-01-15",
                    "borough": "BRONX",
                    "management_program": "PVT",
                    "complaint_count": 4,
                    "no_heat_count": 3,
                    "hot_water_problem_count": 1,
                    "rolling_7d_complaints": 8,
                    "rolling_7d_request_count": 10,
                    "open_linked_violation_count": 12,
                    "unit_count_proxy": 6,
                    "heat_sensor_unit_count": 10,
                    "days_since_last_complaint": -1,
                    "weather_heating_degree_c": 7,
                    "weather_freezing_any_flag": 1,
                    "weather_cold_shock_flag": 1,
                    "weather_temp_drop_c": 3,
                    "cre_vulnerability_index": 0.8,
                    "next_day_complaint_count": 2,
                }
            ]
        )

        prepared = prepare_feature_frame(frame, compute_target=True)
        row = prepared.iloc[0]

        self.assertEqual(row["unit_count_effective"], 10)
        self.assertAlmostEqual(row["open_violation_per_unit"], 1.2)
        self.assertAlmostEqual(row["rolling_7d_complaints_per_unit"], 0.8)
        self.assertEqual(row["days_since_last_complaint_capped"], 30)
        self.assertAlmostEqual(row["no_heat_share"], 0.75)
        self.assertAlmostEqual(row["hot_water_share"], 0.25)
        self.assertAlmostEqual(row["weather_severity_index"], 14.0)
        self.assertAlmostEqual(row["equity_weather_interaction"], 11.2)
        self.assertEqual(row["target"], 1)

    def test_prepare_feature_frame_fills_missing_defaults(self) -> None:
        prepared = prepare_feature_frame(pd.DataFrame([{"calendar_date": "2025-02-01"}]), compute_target=False)
        row = prepared.iloc[0]

        self.assertEqual(row["borough"], "UNKNOWN")
        self.assertEqual(row["management_program"], "unknown")
        self.assertEqual(row["unit_count_effective"], 1)
        self.assertEqual(row["open_violation_per_unit"], 0)
        self.assertEqual(row["equity_weather_interaction"], 0)


if __name__ == "__main__":
    unittest.main()
