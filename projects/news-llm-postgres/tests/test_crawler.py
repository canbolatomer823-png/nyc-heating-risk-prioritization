import unittest

from news_pipeline.fetchers import extract_article_from_html, extract_article_links, extract_reddit_post_links
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

    def test_extracts_reddit_post_links_from_old_reddit_listing(self):
        html = """
        <html>
          <body>
            <div class="thing link stickied">
              <a class="title" href="/r/Turkey/comments/sticky/sticky_post/">Sticky</a>
              <a class="comments" href="/r/Turkey/comments/sticky/sticky_post/">comments</a>
            </div>
            <div class="thing link">
              <a class="title" href="https://i.redd.it/image.jpeg">Image</a>
              <a class="comments" href="/r/Turkey/comments/abc123/baslik/">comments</a>
            </div>
            <div class="thing link">
              <a class="title" href="/r/AskTurkey/comments/def456/baska/">Other subreddit</a>
              <a class="comments" href="/r/AskTurkey/comments/def456/baska/">comments</a>
            </div>
          </body>
        </html>
        """

        links = extract_reddit_post_links(html, "https://old.reddit.com/r/Turkey/", limit=10)

        self.assertEqual(
            links,
            [
                "https://old.reddit.com/r/Turkey/comments/abc123/baslik",
            ],
        )

    def test_extracts_reddit_post_title_body_and_comments(self):
        source = NewsSource(
            key="reddit_turkey",
            name="Reddit r/Turkey",
            homepage="https://www.reddit.com/r/Turkey/",
            source_type="reddit",
            crawl_url="https://old.reddit.com/r/Turkey/",
        )
        html = """
        <html>
          <body>
            <div class="thing link">
              <a class="title">Ekonomi hakkında Reddit başlığı</a>
              <div class="usertext-body"><p>Post içeriği burada yer alıyor.</p></div>
            </div>
            <div class="comment">
              <div class="usertext-body"><p>İlk yorum metni.</p></div>
            </div>
            <div class="comment">
              <div class="usertext-body"><p>İkinci yorum metni.</p></div>
            </div>
          </body>
        </html>
        """

        item = extract_article_from_html(
            html,
            "https://old.reddit.com/r/Turkey/comments/abc123/baslik/",
            source,
        )

        self.assertEqual(item.title, "Ekonomi hakkında Reddit başlığı")
        self.assertIn("Post içeriği", item.summary)
        self.assertIn("İlk yorum metni", item.content_text)
        self.assertEqual(item.raw["source_type"], "reddit")
        self.assertEqual(item.raw["comments_sampled"], 2)


if __name__ == "__main__":
    unittest.main()
