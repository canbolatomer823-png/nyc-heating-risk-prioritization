import unittest

from news_pipeline.fetchers import extract_article_from_html, extract_article_links
from news_pipeline.models import NewsSource


class CrawlerTest(unittest.TestCase):
    def test_extracts_probable_article_links_from_listing_page(self):
        source = NewsSource(
            key="example",
            name="Example",
            homepage="https://news.example.com",
            crawl_url="https://news.example.com",
            allowed_domains=["news.example.com"],
            article_url_patterns=[r"news\.example\.com/haber/.+-\d+"],
            exclude_url_patterns=[r"/video/"],
        )
        html = """
        <html>
          <body>
            <a href="/haber/ekonomi-faiz-karari-123">Ekonomi haberi</a>
            <a href="/video/spor-ozeti-456">Video</a>
            <a href="https://other.example.com/haber/dis-kaynak-789">Dış kaynak</a>
          </body>
        </html>
        """

        links = extract_article_links(html, "https://news.example.com", source, limit=10)

        self.assertEqual(links, ["https://news.example.com/haber/ekonomi-faiz-karari-123"])

    def test_extracts_title_summary_date_and_text_from_article_page(self):
        source = NewsSource(
            key="example",
            name="Example",
            homepage="https://news.example.com",
            crawl_url="https://news.example.com",
        )
        html = """
        <html>
          <head>
            <meta name="description" content="Kısa açıklama">
            <meta property="article:published_time" content="2026-06-20T10:00:00Z">
            <meta name="keywords" content="ekonomi, faiz">
          </head>
          <body>
            <article>
              <h1>Merkez Bankası faiz kararını açıkladı</h1>
              <p>Bu paragraf yeterince uzun olduğu için haber metnine dahil edilir.</p>
              <p>Kısa.</p>
              <p>Piyasalar karar sonrası ilk tepkiyi verirken dolar ve altın da izlendi.</p>
            </article>
          </body>
        </html>
        """

        item = extract_article_from_html(html, "https://news.example.com/haber/1", source)

        self.assertEqual(item.title, "Merkez Bankası faiz kararını açıkladı")
        self.assertEqual(item.summary, "Kısa açıklama")
        self.assertEqual(item.published_at, "2026-06-20T10:00:00Z")
        self.assertEqual(item.tags, ["ekonomi", "faiz"])
        self.assertIn("Piyasalar karar sonrası", item.content_text)


if __name__ == "__main__":
    unittest.main()
