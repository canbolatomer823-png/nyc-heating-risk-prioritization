from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting.build_final_project_audit import AuditItem, count_csv_rows, parse_env_file, summarize


class FinalProjectAuditTest(unittest.TestCase):
    def test_parse_env_file_skips_comments_and_blanks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "aws.env"
            path.write_text("\n# comment\nAWS_REGION=us-east-1\nAWS_ACCOUNT_ID=123456789012\n", encoding="utf-8")

            values = parse_env_file(path)

        self.assertEqual(values["AWS_REGION"], "us-east-1")
        self.assertEqual(values["AWS_ACCOUNT_ID"], "123456789012")

    def test_count_csv_rows_uses_data_rows_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rows.csv"
            path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

            self.assertEqual(count_csv_rows(path), 2)

    def test_summarize_treats_warnings_as_known_blockers(self) -> None:
        status, counts = summarize(
            [
                AuditItem("OK", "model", "model", "ok"),
                AuditItem("WARN", "aws", "credentials", "pending"),
            ]
        )

        self.assertEqual(status, "READY_WITH_KNOWN_BLOCKERS")
        self.assertEqual(counts, "0 fail, 1 warn")


if __name__ == "__main__":
    unittest.main()
