import unittest

from news_pipeline.llm import AnalysisResult
from news_pipeline.models import NewsSource, RawNewsItem
from news_pipeline.pipeline import build_payload, content_hash_for_item


class PayloadTest(unittest.TestCase):
    def test_payload_keeps_dynamic_fields_under_jsonb_shape(self):
        source = NewsSource(
            key="test",
            name="Test",
            homepage="https://example.com",
            feed_url="https://example.com/rss",
        )
        item = RawNewsItem(source=source, title="Başlık", url="https://example.com/news")
        analysis = AnalysisResult(
            category="diger",
            subcategory="diger",
            sentiment="neutral",
            summary="Kısa özet",
            keywords=["test"],
            confidence=0.5,
            analyzer="fallback_rules",
        )

        payload = build_payload(item, analysis)

        self.assertEqual(payload["schema_version"], "news-item-v1")
        self.assertEqual(payload["source"]["key"], "test")
        self.assertEqual(payload["article"]["title"], "Başlık")
        self.assertEqual(payload["analysis"]["category"], "diger")
        self.assertEqual(payload["pipeline"]["content_hash"], content_hash_for_item(item))

    def test_content_hash_is_stable(self):
        source = NewsSource(
            key="test",
            name="Test",
            homepage="https://example.com",
            feed_url="https://example.com/rss",
        )
        item = RawNewsItem(source=source, title="A", url="https://example.com/news")

        self.assertEqual(content_hash_for_item(item), content_hash_for_item(item))


if __name__ == "__main__":
    unittest.main()
