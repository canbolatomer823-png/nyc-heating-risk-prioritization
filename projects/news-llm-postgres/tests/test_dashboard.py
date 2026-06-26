import json
import tempfile
import unittest
from pathlib import Path

from news_pipeline.dashboard import build_dashboard


class DashboardTest(unittest.TestCase):
    def test_builds_standalone_dashboard_html(self):
        payload = {
            "source": {"key": "test", "name": "Test"},
            "article": {"title": "Merkez Bankası faiz kararını açıkladı", "url": "https://example.com/1"},
            "analysis": {
                "category": "ekonomi",
                "event_type": "market_update",
                "topics": ["ekonomi", "faiz"],
            },
            "cluster": {"cluster_size": 2},
            "pipeline": {"collected_at": "2026-06-26T10:00:00Z"},
        }
        patterns = {
            "total_documents": 1,
            "category_counts": [{"value": "ekonomi", "count": 1}],
            "event_type_counts": [{"value": "market_update", "count": 1}],
            "source_counts": [{"value": "test", "count": 1}],
            "top_topics": [{"value": "faiz", "count": 1}],
            "geography_counts": [{"value": "Türkiye", "count": 1}],
            "risk_flag_counts": [{"value": "market_pressure", "count": 1}],
            "clusters": [
                {
                    "cluster_id": "cluster_1",
                    "cluster_size": 2,
                    "representative_title": "Faiz kararı",
                    "common_terms": ["faiz"],
                    "sources": ["test"],
                    "urls": ["https://example.com/1"],
                }
            ],
            "observations": ["Benzer haber kümeleri bulundu"],
            "pipeline": {
                "generated_at": "2026-06-26T10:05:00Z",
                "errors": [
                    {
                        "source": "twitter_turkey_news",
                        "error": "Twitter/X public HTML did not expose post text.",
                    }
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            payloads_path = root / "payloads.jsonl"
            patterns_path = root / "patterns.json"
            output_path = root / "dashboard.html"
            payloads_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
            patterns_path.write_text(json.dumps(patterns, ensure_ascii=False), encoding="utf-8")

            result = build_dashboard(payloads_path, patterns_path, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertEqual(result["status"], "ok")
            self.assertIn("News Pattern Dashboard", html)
            self.assertIn("İçgörü", html)
            self.assertIn("Entity / Topic Ağı", html)
            self.assertIn("Haber İnceleme", html)
            self.assertIn("Etki skoru", html)
            self.assertIn("Faiz kararı", html)
            self.assertIn("twitter_turkey_news", html)


if __name__ == "__main__":
    unittest.main()
