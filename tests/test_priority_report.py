from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.build_inspection_priority_report import explanation_rows, latest_priority_rows_from_csv


class PriorityReportTest(unittest.TestCase):
    def test_latest_priority_rows_streams_latest_test_day_only(self) -> None:
        rows = [
            {
                "building_id": "10",
                "calendar_date": "2025-05-29",
                "data_split": "test",
                "model_probability": "0.9",
                "cre_vulnerability_index": "0.5",
            },
            {
                "building_id": "20",
                "calendar_date": "2025-05-30",
                "data_split": "train",
                "model_probability": "0.99",
                "cre_vulnerability_index": "1.0",
            },
            {
                "building_id": "30",
                "calendar_date": "2025-05-30",
                "data_split": "test",
                "model_probability": "0.4",
                "cre_vulnerability_index": "0.2",
            },
            {
                "building_id": "40",
                "calendar_date": "2025-05-30",
                "data_split": "test",
                "model_probability": "0.7",
                "cre_vulnerability_index": "0.1",
            },
            {
                "building_id": "50",
                "calendar_date": "2025-05-30",
                "data_split": "test",
                "model_probability": "0.6",
                "cre_vulnerability_index": "0.5",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "scored.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "building_id",
                        "calendar_date",
                        "data_split",
                        "model_probability",
                        "cre_vulnerability_index",
                    ],
                )
                writer.writeheader()
                writer.writerows(rows)

            latest_date, priority_rows = latest_priority_rows_from_csv(csv_path, top_n=2)

        self.assertEqual(latest_date, "2025-05-30")
        self.assertEqual([row["building_id"] for row in priority_rows], ["50", "40"])
        self.assertEqual(priority_rows[0]["equity_weighted_priority_score"], "0.900000")
        self.assertEqual(priority_rows[1]["equity_weighted_priority_score"], "0.770000")

    def test_explanation_rows_keeps_why_risky_fields(self) -> None:
        rows = [
            {
                "inspection_priority_rank": "1",
                "calendar_date": "2025-05-30",
                "building_id": "50",
                "borough": "BRONX",
                "incident_address": "123 MAIN ST",
                "model_probability": "0.91",
                "equity_weighted_priority_score": "1.22",
                "why_risky": "Riski yukselten baslica sinyaller: prior complaint days=10.",
                "top_positive_contributors": "prior complaint days=10 (+1.0)",
                "top_negative_contributors": "avg temp=18 (-0.5)",
                "extra_column": "not exported",
            }
        ]

        output_rows = explanation_rows(rows)

        self.assertEqual(output_rows[0]["why_risky"], rows[0]["why_risky"])
        self.assertEqual(output_rows[0]["top_positive_contributors"], rows[0]["top_positive_contributors"])
        self.assertEqual(output_rows[0]["top_negative_contributors"], rows[0]["top_negative_contributors"])
        self.assertNotIn("extra_column", output_rows[0])


if __name__ == "__main__":
    unittest.main()
