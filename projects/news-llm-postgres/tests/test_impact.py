from __future__ import annotations

import unittest

from news_pipeline.impact import apply_macro_impact_analysis, build_macro_impact_report
from news_pipeline.models import AnalysisResult, NewsSource, RawNewsItem
from news_pipeline.pipeline import build_payload


class MacroImpactTest(unittest.TestCase):
    def test_scores_economy_news_between_minus_five_and_plus_five(self):
        payload = self.payload_for(
            title="Merkez Bankası faiz ve enflasyon görünümünü değerlendirdi",
            category="ekonomi",
            summary="Dolar, TL, enflasyon ve piyasa beklentileri yakından izleniyor.",
            content_text="Merkez Bankası faiz kararının ardından piyasa güveni, TL ve enflasyon beklentileri öne çıktı.",
        )

        apply_macro_impact_analysis([payload])

        impact = payload["impact_analysis"]
        self.assertTrue(impact["eligible"])
        self.assertGreater(impact["net_abs_impact"], 0)
        for row in impact["indicator_scores"]:
            self.assertGreaterEqual(row["score"], -5)
            self.assertLessEqual(row["score"], 5)

    def test_excludes_surface_celebrity_death_from_macro_impact(self):
        payload = self.payload_for(
            title="Cumhurbaşkanı Erdoğan Kadir İnanır için başsağlığı mesajı yayımladı",
            category="siyaset",
            summary="Kadir İnanır'ın vefatı sonrası taziye mesajları paylaşıldı.",
            content_text="Türk sinemasının usta oyuncusu Kadir İnanır için sanat camiasından mesajlar geldi.",
        )

        apply_macro_impact_analysis([payload])

        self.assertFalse(payload["impact_analysis"]["eligible"])
        self.assertEqual(payload["impact_analysis"]["net_abs_impact"], 0)
        self.assertIn("yüzeysel", payload["impact_analysis"]["excluded_reason"])

    def test_report_contains_trends_and_break_analysis(self):
        payloads = [
            self.payload_for(
                title="Merkez Bankası faiz kararını açıkladı",
                category="ekonomi",
                summary="Enflasyon ve TL beklentileri izleniyor.",
                content_text="Merkez Bankası faiz kararı piyasa güveni için takip ediliyor.",
                published_at="2026-06-26T10:00:00+03:00",
            ),
            self.payload_for(
                title="Dolar ve enflasyon beklentileri piyasada öne çıktı",
                category="ekonomi",
                summary="TL, dolar ve enflasyon başlıkları gündemde.",
                content_text="Piyasada dolar kuru ve enflasyon baskısı yakından izleniyor.",
                published_at="2026-06-26T11:00:00+03:00",
            ),
        ]
        apply_macro_impact_analysis(payloads)

        report = build_macro_impact_report(payloads)

        self.assertEqual(report["eligible_documents"], 2)
        self.assertGreaterEqual(len(report["trend_report"]["top_trends"]), 1)
        self.assertGreaterEqual(len(report["major_breaks"]), 1)

    def payload_for(
        self,
        title: str,
        category: str,
        summary: str,
        content_text: str,
        published_at: str | None = "2026-06-26T10:00:00+03:00",
    ):
        source = NewsSource(
            key="test",
            name="Test",
            homepage="https://example.com",
            crawl_url="https://example.com",
        )
        item = RawNewsItem(
            source=source,
            title=title,
            url=f"https://example.com/{abs(hash(title))}",
            summary=summary,
            content_text=content_text,
            published_at=published_at,
        )
        analysis = AnalysisResult(
            category=category,
            subcategory=category,
            sentiment="neutral",
            summary=summary,
            keywords=["faiz", "enflasyon", "tl"],
            confidence=0.8,
            analyzer="test",
            topics=[category, "faiz", "enflasyon"],
            event_type="market_update" if category == "ekonomi" else "statement",
            geography=["Türkiye"],
            importance="high",
            risk_flags=["market_pressure"] if category == "ekonomi" else ["political_tension"],
        )
        return build_payload(item, analysis)


if __name__ == "__main__":
    unittest.main()
