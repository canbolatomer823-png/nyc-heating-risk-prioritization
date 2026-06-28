import unittest

from news_pipeline.clustering import apply_clusters, build_pattern_report
from news_pipeline.insights import enrich_pattern_report
from news_pipeline.models import AnalysisResult, NewsSource, RawNewsItem
from news_pipeline.pipeline import build_payload


class InsightsTest(unittest.TestCase):
    def test_enriches_patterns_with_source_health_cluster_rankings_and_network(self):
        ok_source = NewsSource(
            key="ok_news",
            name="OK News",
            homepage="https://example.com",
            crawl_url="https://example.com",
        )
        blocked_source = NewsSource(
            key="twitter_turkey_news",
            name="Twitter/X",
            homepage="https://x.com",
            source_type="twitter",
        )
        payloads = [
            self.payload_for(ok_source, "Merkez Bankası faiz kararını açıkladı", "https://example.com/1"),
            self.payload_for(ok_source, "Merkez Bankası faiz kararını duyurdu", "https://example.com/2"),
        ]
        apply_clusters(payloads)
        patterns = build_pattern_report(payloads)

        enriched = enrich_pattern_report(
            patterns=patterns,
            payloads=payloads,
            sources=[ok_source, blocked_source],
            errors=[
                {
                    "source": "twitter_turkey_news",
                    "stage": "html_crawl",
                    "error": "blocked",
                }
            ],
        )

        self.assertIn("source_health", enriched)
        self.assertIn("cluster_rankings", enriched)
        self.assertIn("entity_network", enriched)
        self.assertIn("outlier_report", enriched)
        self.assertIn("decision_summary", enriched)
        self.assertIn("insight_cards", enriched)
        self.assertEqual(enriched["source_health"][0]["key"], "twitter_turkey_news")
        self.assertEqual(enriched["source_health"][0]["status"], "blocked")
        self.assertEqual(enriched["cluster_rankings"][0]["cluster_size"], 2)
        self.assertGreater(enriched["cluster_rankings"][0]["impact_score"], 0)
        self.assertGreaterEqual(len(enriched["outlier_report"]["cluster_outliers"]), 1)
        self.assertIn("decision_label", enriched["decision_summary"])
        self.assertGreaterEqual(len(enriched["insight_cards"]), 2)

    def payload_for(self, source: NewsSource, title: str, url: str):
        item = RawNewsItem(source=source, title=title, url=url, summary=title)
        analysis = AnalysisResult(
            category="ekonomi",
            subcategory="market_update",
            sentiment="neutral",
            summary=title,
            keywords=["merkez", "bankası", "faiz", "karar"],
            confidence=0.8,
            analyzer="test",
            topics=["ekonomi", "faiz", "merkez bankası"],
            entities={
                "persons": [],
                "organizations": ["Merkez Bankası"],
                "locations": ["Türkiye"],
            },
            event_type="market_update",
            geography=["Türkiye"],
            importance="high",
            risk_flags=["market_pressure"],
        )
        return build_payload(item, analysis)


if __name__ == "__main__":
    unittest.main()
