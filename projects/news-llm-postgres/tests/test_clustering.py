import unittest

from news_pipeline.clustering import apply_clusters, build_pattern_report
from news_pipeline.models import AnalysisResult, NewsSource, RawNewsItem
from news_pipeline.pipeline import build_payload


class ClusteringTest(unittest.TestCase):
    def test_groups_similar_news_and_keeps_unrelated_news_separate(self):
        payloads = [
            self.payload_for(
                title="Merkez Bankası faiz kararını açıkladı",
                url="https://example.com/1",
                category="ekonomi",
                keywords=["merkez", "bankası", "faiz", "karar"],
            ),
            self.payload_for(
                title="Merkez Bankası faiz kararını duyurdu",
                url="https://example.com/2",
                category="ekonomi",
                keywords=["merkez", "bankası", "faiz", "karar"],
            ),
            self.payload_for(
                title="Fenerbahçe transfer görüşmelerine başladı",
                url="https://example.com/3",
                category="spor",
                keywords=["fenerbahçe", "transfer"],
            ),
        ]

        apply_clusters(payloads)

        self.assertEqual(payloads[0]["cluster"]["cluster_id"], payloads[1]["cluster"]["cluster_id"])
        self.assertEqual(payloads[0]["cluster"]["cluster_size"], 2)
        self.assertEqual(payloads[2]["cluster"]["cluster_size"], 1)

    def test_builds_pattern_report_from_clustered_payloads(self):
        payloads = [
            self.payload_for(
                title="Merkez Bankası faiz kararını açıkladı",
                url="https://example.com/1",
                category="ekonomi",
                keywords=["merkez", "bankası", "faiz", "karar"],
            ),
            self.payload_for(
                title="Merkez Bankası faiz kararını duyurdu",
                url="https://example.com/2",
                category="ekonomi",
                keywords=["merkez", "bankası", "faiz", "karar"],
            ),
        ]
        apply_clusters(payloads)

        report = build_pattern_report(payloads)

        self.assertEqual(report["total_documents"], 2)
        self.assertEqual(len(report["clusters"]), 1)
        self.assertEqual(report["clusters"][0]["cluster_size"], 2)
        self.assertIn("observations", report)

    def payload_for(self, title: str, url: str, category: str, keywords: list[str]):
        source = NewsSource(
            key="test",
            name="Test",
            homepage="https://example.com",
            crawl_url="https://example.com",
        )
        item = RawNewsItem(source=source, title=title, url=url, summary=title)
        analysis = AnalysisResult(
            category=category,
            subcategory=category,
            sentiment="neutral",
            summary=title,
            keywords=keywords,
            confidence=0.7,
            analyzer="test",
            topics=[category, *keywords],
            risk_flags=["market_pressure"] if category == "ekonomi" else [],
        )
        return build_payload(item, analysis)


if __name__ == "__main__":
    unittest.main()
