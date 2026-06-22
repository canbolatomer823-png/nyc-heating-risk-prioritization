import unittest

from news_pipeline.llm import RuleBasedAnalyzer
from news_pipeline.models import NewsSource, RawNewsItem


class RuleBasedAnalyzerTest(unittest.TestCase):
    def test_classifies_economy_news(self):
        source = NewsSource(
            key="test",
            name="Test",
            homepage="https://example.com",
            crawl_url="https://example.com",
        )
        item = RawNewsItem(
            source=source,
            title="Merkez Bankası faiz kararını açıkladı",
            url="https://example.com/1",
            summary="Dolar, enflasyon ve piyasa beklentileri yakından izleniyor.",
        )

        result = RuleBasedAnalyzer().analyze(item)

        self.assertEqual(result.category, "ekonomi")
        self.assertGreaterEqual(result.confidence, 0.5)
        self.assertIn("market_pressure", result.risk_flags)
        self.assertIn("ekonomi", result.topics)
        self.assertIn(result.importance, {"high", "critical"})


if __name__ == "__main__":
    unittest.main()
