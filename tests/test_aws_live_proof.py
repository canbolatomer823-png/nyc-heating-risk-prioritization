from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aws.capture_live_deploy_proof import is_remote_url
from aws.capture_shutdown_proof import host_from_url


class AwsLiveProofUrlTest(unittest.TestCase):
    def test_rejects_local_urls(self) -> None:
        self.assertFalse(is_remote_url("http://127.0.0.1:8000"))
        self.assertFalse(is_remote_url("http://localhost:8000"))
        self.assertFalse(is_remote_url("http://demo.local:8000"))

    def test_accepts_remote_http_urls(self) -> None:
        self.assertTrue(is_remote_url("http://abc.elb.amazonaws.com"))
        self.assertTrue(is_remote_url("https://api.example.com"))

    def test_rejects_non_http_urls(self) -> None:
        self.assertFalse(is_remote_url("file:///tmp/demo.html"))


class AwsShutdownProofTest(unittest.TestCase):
    def test_extracts_host_from_live_proof_url(self) -> None:
        self.assertEqual(host_from_url("http://abc.elb.amazonaws.com/path"), "abc.elb.amazonaws.com")

    def test_empty_live_proof_url_has_no_host(self) -> None:
        self.assertIsNone(host_from_url(None))
        self.assertIsNone(host_from_url(""))


if __name__ == "__main__":
    unittest.main()
