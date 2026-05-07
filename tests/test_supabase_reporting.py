from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.publish_supabase_reporting import build_reporting_payload, write_publish_receipt


class SupabaseReportingTest(unittest.TestCase):
    def test_payload_keeps_operational_priority_fields_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            priority_csv = tmp / "priority.csv"
            metadata_json = tmp / "metadata.json"
            demo_dir = tmp / "demo"
            demo_dir.mkdir()

            rows = [
                {
                    "calendar_date": "2025-05-30",
                    "inspection_priority_rank": "1",
                    "building_id": "65175",
                    "building_bbl": "2026100012.0",
                    "borough": "BRONX",
                    "incident_address": "530 EAST 169 STREET",
                    "building_zip": "10456.0",
                    "community_board": "3.0",
                    "census_tract": "145.0",
                    "raw_model_probability": "0.9999",
                    "model_probability": "0.9714",
                    "model_threshold": "0.2",
                    "model_prediction": "1",
                    "equity_weighted_priority_score": "1.661028",
                    "cre_vulnerability_index": "0.7099",
                    "cre_high_vulnerability_flag": "1",
                    "open_linked_violation_count": "0",
                    "cumulative_complaints_prior": "645",
                    "days_since_last_complaint_capped": "6",
                    "heat_sensor_program_flag": "1",
                    "heat_sensor_active_flag": "0",
                    "weather_heating_degree_c": "0.0",
                    "weather_freezing_any_flag": "0",
                    "why_risky": "Riski yukselten baslica sinyaller: prior complaint days=167.",
                    "top_positive_contributors": "prior complaint days=167 (+10.4603)",
                    "top_negative_contributors": "average temperature=18 (-1.7206)",
                    "top_positive_contributors_json": '[{"feature": "num__complaint_day_count_prior", "contribution": 10.4603}]',
                    "top_negative_contributors_json": '[{"feature": "num__weather_avg_temp_c", "contribution": -1.7206}]',
                    "full_panel_extra_column": "must not be exported",
                }
            ]
            with priority_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

            metadata_json.write_text(
                json.dumps(
                    {
                        "model_type": "logistic_regression",
                        "calibration_method": "platt",
                        "threshold": 0.2,
                        "created_at_utc": "2026-04-24T12:08:23+00:00",
                        "metrics": {"test": {"rows": 1762330}},
                    }
                ),
                encoding="utf-8",
            )
            (demo_dir / "health.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

            payload = build_reporting_payload(
                priority_csv_path=priority_csv,
                metadata_json_path=metadata_json,
                window_label="test-window",
                demo_proof_dir=demo_dir,
            )

        self.assertEqual(payload["model_run"]["priority_date"], "2025-05-30")
        self.assertEqual(payload["model_run"]["priority_row_count"], 1)
        self.assertEqual(payload["model_run"]["scored_row_count"], 1762330)
        self.assertEqual(payload["daily_priority_buildings"][0]["building_id"], "65175")
        self.assertNotIn("full_panel_extra_column", payload["daily_priority_buildings"][0])
        self.assertIn("prior complaint days", payload["prediction_explanations"][0]["why_risky"])
        self.assertEqual(payload["prediction_explanations"][0]["top_positive_contributors_json"][0]["contribution"], 10.4603)
        self.assertEqual(payload["demo_proof_events"][0]["event_type"], "health")

    def test_write_publish_receipt_records_database_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            receipt_path = write_publish_receipt(
                {
                    "published_at_utc": "2026-05-01T00:00:00+00:00",
                    "model_run_id": "run-1",
                    "priority_rows": 50,
                    "explanation_rows": 50,
                    "demo_events": 5,
                    "total_model_runs": 1,
                },
                Path(tmpdir),
            )

            text = receipt_path.read_text(encoding="utf-8")

        self.assertIn("Supabase Publish Receipt", text)
        self.assertIn("Priority rows written: `50`", text)
        self.assertIn("Explanation rows written: `50`", text)


if __name__ == "__main__":
    unittest.main()
