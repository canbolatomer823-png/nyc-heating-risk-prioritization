from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.check_supabase_readiness import CheckResult, mask_db_url, summarize, validate_payload_shape


class SupabaseReadinessTest(unittest.TestCase):
    def test_mask_db_url_hides_password_and_query(self) -> None:
        masked = mask_db_url(
            "postgresql://postgres.abc:secret-password@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
        )

        self.assertEqual(masked, "postgresql://postgres.abc:***@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
        self.assertNotIn("secret-password", masked)
        self.assertNotIn("sslmode", masked)

    def test_validate_payload_shape_accepts_expected_counts(self) -> None:
        results: list[CheckResult] = []
        payload = {
            "model_run": {"model_run_id": "run-1", "priority_date": "2025-05-30"},
            "daily_priority_buildings": [{"building_id": str(index), "model_probability": 0.5} for index in range(50)],
            "prediction_explanations": [{"building_id": str(index), "why_risky": "x"} for index in range(50)],
            "demo_proof_events": [{"event_type": f"event_{index}"} for index in range(5)],
        }

        validate_payload_shape(payload, results)

        self.assertTrue(all(result.status == "OK" for result in results))

    def test_summarize_fails_on_any_failure(self) -> None:
        status, counts = summarize([CheckResult("OK", "a", "b"), CheckResult("FAIL", "x", "y")])

        self.assertEqual(status, "NEEDS_FIX")
        self.assertEqual(counts, "1 fail, 0 warn")


if __name__ == "__main__":
    unittest.main()
