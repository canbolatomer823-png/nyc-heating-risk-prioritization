from __future__ import annotations

import os
import sys
import unittest
import warnings
from pathlib import Path
from unittest import mock

import pandas as pd
from fastapi.testclient import TestClient

warnings.filterwarnings(
    "ignore",
    message=r"The 'app' shortcut is now deprecated.*",
    category=DeprecationWarning,
    module=r"httpx\._client",
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ["NYC_HEAT_MODEL_BUNDLE"] = str(
    PROJECT_ROOT / "data" / "windows" / "heat_season_2024_10_01_2025_05_31" / "models" / "logistic_regression_bundle.joblib"
)
os.environ["NYC_HEAT_PRIORITY_CSV"] = str(
    PROJECT_ROOT / "data" / "windows" / "heat_season_2024_10_01_2025_05_31" / "reports" / "inspection_priority_latest_day.csv"
)
os.environ["NYC_HEAT_RECORD_LOOKUP_DB"] = str(
    PROJECT_ROOT / "data" / "windows" / "heat_season_2024_10_01_2025_05_31" / "processed" / "record_lookup.sqlite"
)
os.environ["NYC_HEAT_SCORED_CSV"] = str(
    PROJECT_ROOT / "data" / "windows" / "heat_season_2024_10_01_2025_05_31" / "processed" / "logistic_regression_scored.csv"
)
os.environ.pop("NYC_HEAT_S3_BUCKET", None)
os.environ.pop("NYC_HEAT_S3_PREFIX", None)
os.environ.pop("NYC_HEAT_S3_MODEL_KEY", None)
os.environ.pop("NYC_HEAT_S3_PRIORITY_KEY", None)
os.environ.pop("NYC_HEAT_S3_SCORED_KEY", None)

from api import app as api_module
from project_paths import FINAL_DENSE_PANEL_PATH


def to_native(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


class ApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        api_module.load_bundle.cache_clear()
        api_module.load_priority_frame.cache_clear()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cls.client = TestClient(api_module.app)
        sample_row = pd.read_csv(FINAL_DENSE_PANEL_PATH, nrows=1, low_memory=False).iloc[0].to_dict()
        cls.sample_payload = {key: to_native(value) for key, value in sample_row.items()}

    def test_health_endpoint_reports_loaded_artifacts(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], ("ok", "degraded"))
        self.assertTrue(payload["model_accessible"])
        self.assertTrue(payload["priority_accessible"])
        self.assertTrue(payload["lookup_db_accessible"])
        self.assertTrue(payload["scored_accessible"])
        self.assertTrue(payload["record_lookup_db_loaded"])
        self.assertTrue(payload["scored_csv_present"])
        self.assertTrue(payload["scored_csv_readable"])
        self.assertTrue(payload["priority_csv_loaded"])
        self.assertGreater(payload["scored_row_count"], 0)
        self.assertGreater(payload["priority_row_count"], 0)
        self.assertEqual(payload["model_type"], "logistic_regression")
        self.assertEqual(payload["artifact_source"]["type"], "local")

    def test_metadata_endpoint_returns_latest_priority_date(self) -> None:
        response = self.client.get("/metadata")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model_type"], "logistic_regression")
        self.assertIn("latest_priority_date", payload)
        self.assertGreater(payload["scored_row_count"], 0)
        self.assertGreater(payload["priority_row_count"], 0)

    def test_priority_and_record_endpoints_round_trip(self) -> None:
        response = self.client.get("/priorities/latest", params={"top_n": 5})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["top_n"], 5)
        self.assertGreater(len(payload["rows"]), 0)

        first_row = payload["rows"][0]
        record = self.client.get(
            f"/records/{first_row['building_id']}",
            params={"calendar_date": first_row["calendar_date"]},
        )
        self.assertEqual(record.status_code, 200)
        self.assertEqual(str(record.json()["row"]["building_id"]), str(first_row["building_id"]))
        self.assertEqual(record.json()["row"]["calendar_date"], first_row["calendar_date"])

    def test_dashboard_endpoint_returns_operational_html(self) -> None:
        response = self.client.get("/dashboard", params={"top_n": 5})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("NYC heating complaint risk dashboard", response.text)
        self.assertIn("Why risky", response.text)

    def test_showcase_endpoint_returns_interactive_project_site(self) -> None:
        response = self.client.get("/showcase")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("NYC Heating Risk | İnteraktif Proje Deneyimi", response.text)
        self.assertIn("Saha brifingi", response.text)
        self.assertIn("NYC risk haritası", response.text)
        self.assertIn("Risk keşfi", response.text)
        self.assertIn("priorityRows", response.text)

    def test_home_endpoint_returns_project_showcase(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Şikayet gelmeden önce", response.text)

    def test_record_endpoint_uses_lookup_db_before_csv_scan(self) -> None:
        with mock.patch.object(api_module, "load_priority_frame", return_value=pd.DataFrame(columns=api_module.PRIORITY_COLUMNS)):
            with mock.patch.object(
                api_module,
                "find_record_in_lookup_db",
                return_value={"building_id": "123", "calendar_date": "2025-01-02", "model_probability": 0.42},
            ) as lookup_mock:
                with mock.patch.object(api_module, "find_record_in_scored_csv") as csv_mock:
                    response = self.client.get("/records/123", params={"calendar_date": "2025-01-02"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["row"]["building_id"], "123")
        lookup_mock.assert_called_once_with(building_id="123", calendar_date="2025-01-02")
        csv_mock.assert_not_called()

    def test_s3_health_checks_use_head_probe_not_download(self) -> None:
        with mock.patch.object(api_module, "S3_BUCKET", "demo-bucket"):
            with mock.patch.object(api_module, "S3_SCORED_KEY", "scored/demo.csv"):
                with mock.patch.object(api_module, "S3_RECORD_LOOKUP_KEY", "lookup/demo.sqlite"):
                    with mock.patch.object(api_module, "head_s3_object", return_value={"ContentLength": 128}) as head_mock:
                        with mock.patch.object(api_module, "download_s3_object") as download_mock:
                            self.assertTrue(api_module.scored_csv_is_available())
                            self.assertTrue(api_module.scored_csv_is_readable())
                            self.assertTrue(api_module.record_lookup_db_is_available())
        self.assertEqual(head_mock.call_count, 3)
        download_mock.assert_not_called()

    def test_score_endpoint_returns_probability_and_contributors(self) -> None:
        response = self.client.post("/score", json={"rows": [self.sample_payload]})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["rows"]), 1)
        scored = payload["rows"][0]
        self.assertGreaterEqual(scored["probability"], 0.0)
        self.assertLessEqual(scored["probability"], 1.0)
        self.assertIn("prediction", scored)
        self.assertIn("why_risky", scored)
        self.assertTrue(scored["why_risky"])
        self.assertIn("top_positive_contributors", scored)
        self.assertIn("top_negative_contributors", scored)


if __name__ == "__main__":
    unittest.main()
