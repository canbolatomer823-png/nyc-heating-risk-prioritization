from __future__ import annotations

import re
from typing import Any

from .models import NewsSource, RawNewsItem

DEFAULT_HEADERS = {
    "User-Agent": "news-llm-postgres-draft/0.1 (+learning project)",
    "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.8",
}


def fetch_rss_items(
    source: NewsSource,
    limit: int = 5,
    timeout_seconds: float = 15.0,
) -> list[RawNewsItem]:
    try:
        import feedparser
        import httpx
    except ImportError as exc:
        raise RuntimeError("feedparser and httpx are required. Run `pip install -r requirements.txt`.") from exc

    response = httpx.get(
        source.feed_url,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    items: list[RawNewsItem] = []
    for entry in parsed.entries[:limit]:
        title = clean_text(entry.get("title", ""))
        url = entry.get("link", "")
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]

        if not title or not url:
            continue

        items.append(
            RawNewsItem(
                source=source,
                title=title,
                url=url,
                summary=summary,
                published_at=entry.get("published") or entry.get("updated"),
                author=entry.get("author"),
                tags=tags,
                raw=safe_entry_dict(entry),
            )
        )

    return items


def fetch_article_text(url: str, timeout_seconds: float = 15.0, max_chars: int = 6000) -> str:
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 and httpx are required. Run `pip install -r requirements.txt`.") from exc

    response = httpx.get(
        url,
        headers={**DEFAULT_HEADERS, "Accept": "text/html,application/xhtml+xml"},
        follow_redirects=True,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    paragraphs = [clean_text(p.get_text(" ")) for p in soup.find_all("p")]
    text = "\n".join(paragraph for paragraph in paragraphs if len(paragraph) > 40)
    return text[:max_chars]


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def safe_entry_dict(entry: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("id", "guidislink", "title", "link", "published", "updated", "summary", "author"):
        if key in entry:
            result[key] = entry.get(key)
    return result
