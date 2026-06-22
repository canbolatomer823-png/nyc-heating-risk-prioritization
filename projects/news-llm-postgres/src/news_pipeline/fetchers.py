from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .models import NewsSource, RawNewsItem

DEFAULT_HEADERS = {
    "User-Agent": "news-llm-postgres-draft/0.1 (+learning project)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def crawl_source_items(
    source: NewsSource,
    limit: int = 5,
    timeout_seconds: float = 15.0,
) -> list[RawNewsItem]:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required. Run `pip install -r requirements.txt`.") from exc

    if source.source_type == "twitter":
        return crawl_twitter_items(source, limit=limit, timeout_seconds=timeout_seconds)

    start_url = source.crawl_url or source.homepage
    response = httpx.get(
        start_url,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    if source.source_type == "reddit":
        article_links = extract_reddit_post_links(
            html=response.text,
            base_url=str(response.url),
            limit=max(limit * 4, limit),
        )
    else:
        article_links = extract_article_links(
            html=response.text,
            base_url=str(response.url),
            source=source,
            limit=max(limit * 4, limit),
        )

    items: list[RawNewsItem] = []
    for url in article_links[:limit]:
        try:
            item = fetch_article(url, source=source, timeout_seconds=timeout_seconds)
        except Exception as exc:
            item = RawNewsItem(
                source=source,
                title=url,
                url=url,
                raw={
                    "collector": "html_crawl",
                    "listing_url": start_url,
                    "article_fetch_error": f"{type(exc).__name__}: {exc}",
                },
            )
        items.append(item)

    return items


def crawl_twitter_items(
    source: NewsSource,
    limit: int = 5,
    timeout_seconds: float = 15.0,
) -> list[RawNewsItem]:
    bearer_token = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
    if bearer_token:
        return fetch_twitter_recent_search(source, bearer_token, limit=limit, timeout_seconds=timeout_seconds)

    public_items = fetch_twitter_public_html(source, limit=limit, timeout_seconds=timeout_seconds)
    if public_items:
        return public_items

    raise RuntimeError(
        "Twitter/X public HTML did not expose post text. "
        "Set X_BEARER_TOKEN for the official API, or use a browser/Selenium-style session."
    )


def fetch_twitter_recent_search(
    source: NewsSource,
    bearer_token: str,
    limit: int = 5,
    timeout_seconds: float = 15.0,
) -> list[RawNewsItem]:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required. Run `pip install -r requirements.txt`.") from exc

    query = source.search_query or "Türkiye lang:tr -is:retweet"
    max_results = max(10, min(100, limit))
    response = httpx.get(
        "https://api.x.com/2/tweets/search/recent",
        headers={"Authorization": f"Bearer {bearer_token}"},
        params={
            "query": query,
            "max_results": max_results,
            "sort_order": "recency",
            "tweet.fields": "created_at,author_id,conversation_id,entities,lang,public_metrics,referenced_tweets",
            "expansions": "author_id",
            "user.fields": "name,username,verified,public_metrics",
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return raw_items_from_twitter_api_response(response.json(), source=source, query=query, limit=limit)


def fetch_twitter_public_html(
    source: NewsSource,
    limit: int = 5,
    timeout_seconds: float = 15.0,
) -> list[RawNewsItem]:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required. Run `pip install -r requirements.txt`.") from exc

    start_url = source.crawl_url or twitter_search_url(source.search_query)
    response = httpx.get(
        start_url,
        headers={**DEFAULT_HEADERS, "Accept": "text/html,application/xhtml+xml"},
        follow_redirects=True,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return extract_twitter_posts_from_html(response.text, str(response.url), source, limit=limit)


def fetch_article(url: str, source: NewsSource, timeout_seconds: float = 15.0) -> RawNewsItem:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("httpx is required. Run `pip install -r requirements.txt`.") from exc

    response = httpx.get(
        url,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return extract_article_from_html(response.text, url=str(response.url), source=source)


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


def extract_article_links(
    html: str,
    base_url: str,
    source: NewsSource,
    limit: int = 20,
) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required. Run `pip install -r requirements.txt`.") from exc

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        url = normalize_url(urljoin(base_url, anchor["href"]))
        if url in seen:
            continue
        if not is_probable_article_url(url, source):
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= limit:
            break

    return links


def extract_article_from_html(html: str, url: str, source: NewsSource) -> RawNewsItem:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required. Run `pip install -r requirements.txt`.") from exc

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    if source.source_type == "reddit":
        return extract_reddit_post_from_html(soup, url=url, source=source)

    title = (
        text_of_first(soup, ["h1"])
        or meta_content(soup, "property", "og:title")
        or meta_content(soup, "name", "twitter:title")
        or clean_text(soup.title.get_text(" ") if soup.title else "")
    )
    summary = (
        meta_content(soup, "name", "description")
        or meta_content(soup, "property", "og:description")
        or meta_content(soup, "name", "twitter:description")
    )
    published_at = (
        meta_content(soup, "property", "article:published_time")
        or meta_content(soup, "name", "date")
        or meta_content(soup, "name", "pubdate")
        or first_time_datetime(soup)
    )
    tags = extract_meta_keywords(soup)
    content_text = extract_main_text(soup)

    return RawNewsItem(
        source=source,
        title=title or url,
        url=url,
        summary=summary,
        published_at=published_at,
        tags=tags,
        content_text=content_text,
        raw={
            "collector": "html_crawl",
            "source_type": source.source_type,
            "title_strategy": "h1_or_meta",
            "content_chars": len(content_text),
        },
    )


def extract_reddit_post_links(html: str, base_url: str, limit: int = 20) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required. Run `pip install -r requirements.txt`.") from exc

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    base_subreddit = reddit_subreddit_from_path(urlparse(base_url).path)

    for thing in soup.select(".thing.link"):
        classes = set(thing.get("class", []))
        if "stickied" in classes or "promoted" in classes:
            continue

        comments_link = thing.select_one("a.comments")
        title_link = thing.select_one("a.title")
        href = ""
        if comments_link and comments_link.get("href"):
            href = comments_link.get("href", "")
        elif title_link and title_link.get("href"):
            href = title_link.get("href", "")

        url = normalize_url(urljoin(base_url, href))
        parsed = urlparse(url)
        if "reddit.com" not in parsed.netloc:
            continue
        if "/comments/" not in parsed.path:
            continue
        if base_subreddit and reddit_subreddit_from_path(parsed.path) != base_subreddit:
            continue
        if url in seen:
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= limit:
            break

    return links


def reddit_subreddit_from_path(path: str) -> str:
    match = re.search(r"/r/([^/]+)", path, flags=re.IGNORECASE)
    return match.group(1).lower() if match else ""


def extract_reddit_post_from_html(soup: Any, url: str, source: NewsSource) -> RawNewsItem:
    title = (
        text_of_first(soup, [".thing.link a.title", "a.title"])
        or meta_content(soup, "property", "og:title")
        or clean_text(soup.title.get_text(" ") if soup.title else "")
    )
    post_body = text_of_first(soup, [".thing.link .usertext-body"])
    comments = [
        clean_text(comment.get_text(" "))
        for comment in soup.select(".comment .usertext-body")[:5]
    ]
    comments = [comment for comment in comments if comment]

    content_parts = []
    if post_body:
        content_parts.append(post_body)
    if comments:
        content_parts.append("Top comments:\n" + "\n".join(comments))
    content_text = "\n\n".join(content_parts)

    return RawNewsItem(
        source=source,
        title=title or url,
        url=url,
        summary=post_body[:500],
        content_text=content_text[:8000],
        raw={
            "collector": "html_crawl",
            "source_type": "reddit",
            "comments_sampled": len(comments),
            "content_chars": len(content_text),
        },
    )


def raw_items_from_twitter_api_response(
    data: dict[str, Any],
    source: NewsSource,
    query: str,
    limit: int = 5,
) -> list[RawNewsItem]:
    users = {
        user.get("id"): user
        for user in data.get("includes", {}).get("users", [])
        if user.get("id")
    }
    items: list[RawNewsItem] = []

    for post in data.get("data", [])[:limit]:
        text = clean_text(str(post.get("text", "")))
        if not text:
            continue

        author = users.get(post.get("author_id"), {})
        username = author.get("username")
        post_id = str(post.get("id", ""))
        post_url = twitter_post_url(username=username, post_id=post_id)
        metrics = post.get("public_metrics", {})
        hashtags = extract_twitter_hashtags(post)

        items.append(
            RawNewsItem(
                source=source,
                title=short_title(text),
                url=post_url,
                summary=text[:500],
                published_at=post.get("created_at"),
                author=author.get("name") or username,
                tags=hashtags,
                content_text=text,
                raw={
                    "collector": "twitter_api",
                    "source_type": "twitter",
                    "query": query,
                    "post_id": post_id,
                    "author_id": post.get("author_id"),
                    "username": username,
                    "lang": post.get("lang"),
                    "public_metrics": metrics,
                    "referenced_tweets": post.get("referenced_tweets", []),
                },
            )
        )

    return items


def extract_twitter_posts_from_html(
    html: str,
    base_url: str,
    source: NewsSource,
    limit: int = 5,
) -> list[RawNewsItem]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required. Run `pip install -r requirements.txt`.") from exc

    soup = BeautifulSoup(html, "html.parser")
    items: list[RawNewsItem] = []
    seen: set[str] = set()

    for article in soup.select("article"):
        text_node = article.select_one('[data-testid="tweetText"]') or article
        text = clean_text(text_node.get_text(" "))
        if len(text) < 20:
            continue

        link = first_status_link(article, base_url)
        if not link or link in seen:
            continue
        seen.add(link)

        published_at = None
        time_element = article.find("time")
        if time_element:
            published_at = time_element.get("datetime") or clean_text(time_element.get_text(" "))

        items.append(
            RawNewsItem(
                source=source,
                title=short_title(text),
                url=link,
                summary=text[:500],
                published_at=published_at,
                tags=extract_hashtags_from_text(text),
                content_text=text,
                raw={
                    "collector": "twitter_public_html",
                    "source_type": "twitter",
                    "listing_url": base_url,
                    "note": "Public X HTML is often JS/login gated; this parser only works when post text is server-rendered.",
                },
            )
        )
        if len(items) >= limit:
            break

    for script in soup.find_all("script", type="application/ld+json"):
        if len(items) >= limit:
            break
        try:
            payload = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        for item in twitter_items_from_json_ld(payload, source, base_url):
            if item.url not in seen:
                seen.add(item.url)
                items.append(item)
            if len(items) >= limit:
                break

    return items[:limit]


def twitter_items_from_json_ld(payload: Any, source: NewsSource, base_url: str) -> list[RawNewsItem]:
    records = payload if isinstance(payload, list) else [payload]
    items: list[RawNewsItem] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        text = clean_text(str(record.get("text") or record.get("description") or ""))
        if len(text) < 20:
            continue
        url = normalize_url(urljoin(base_url, str(record.get("url") or "")))
        if "/status/" not in url:
            continue
        author = ""
        if isinstance(record.get("author"), dict):
            author = clean_text(str(record["author"].get("name", "")))
        items.append(
            RawNewsItem(
                source=source,
                title=short_title(text),
                url=url,
                summary=text[:500],
                published_at=record.get("datePublished"),
                author=author or None,
                tags=extract_hashtags_from_text(text),
                content_text=text,
                raw={
                    "collector": "twitter_json_ld",
                    "source_type": "twitter",
                    "listing_url": base_url,
                },
            )
        )
    return items


def first_status_link(article: Any, base_url: str) -> str:
    for anchor in article.find_all("a", href=True):
        href = str(anchor.get("href", ""))
        if "/status/" in href:
            return normalize_url(urljoin(base_url, href))
    return ""


def twitter_search_url(query: str | None) -> str:
    return "https://x.com/search?" + urlencode(
        {
            "q": query or "Türkiye lang:tr -is:retweet",
            "src": "typed_query",
            "f": "live",
        }
    )


def twitter_post_url(username: str | None, post_id: str) -> str:
    if username:
        return f"https://x.com/{username}/status/{post_id}"
    return f"https://x.com/i/web/status/{post_id}"


def extract_twitter_hashtags(post: dict[str, Any]) -> list[str]:
    entities = post.get("entities", {})
    hashtags = entities.get("hashtags", []) if isinstance(entities, dict) else []
    return [
        clean_text(str(hashtag.get("tag", ""))).lower()
        for hashtag in hashtags
        if isinstance(hashtag, dict) and hashtag.get("tag")
    ]


def extract_hashtags_from_text(text: str) -> list[str]:
    return [match.lower() for match in re.findall(r"#([A-Za-z0-9_ğüşöçıİĞÜŞÖÇ]+)", text)]


def short_title(text: str, max_chars: int = 110) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def is_probable_article_url(url: str, source: NewsSource) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not domain_allowed(parsed.netloc, source):
        return False

    path = parsed.path.lower()
    if not path or path == "/":
        return False
    if any(re.search(pattern, url, flags=re.IGNORECASE) for pattern in source.exclude_url_patterns):
        return False
    if any(
        path.endswith(suffix)
        for suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".mp4", ".mp3", ".zip")
    ):
        return False
    if source.article_url_patterns:
        return any(re.search(pattern, url, flags=re.IGNORECASE) for pattern in source.article_url_patterns)

    segments = [segment for segment in path.split("/") if segment]
    has_article_shape = len(segments) >= 2 and ("-" in path or any(char.isdigit() for char in path))
    return has_article_shape


def domain_allowed(hostname: str, source: NewsSource) -> bool:
    hostname = hostname.lower().removeprefix("www.")
    allowed_domains = source.allowed_domains or [urlparse(source.homepage).netloc]
    for domain in allowed_domains:
        normalized = domain.lower().removeprefix("www.")
        if hostname == normalized or hostname.endswith(f".{normalized}"):
            return True
    return False


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or "/",
            "",
            urlencode(query, doseq=True),
            "",
        )
    )


def text_of_first(soup: Any, selectors: list[str]) -> str:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = clean_text(element.get_text(" "))
            if text:
                return text
    return ""


def meta_content(soup: Any, attr: str, value: str) -> str:
    element = soup.find("meta", attrs={attr: value})
    if not element:
        return ""
    return clean_text(element.get("content", ""))


def first_time_datetime(soup: Any) -> str | None:
    element = soup.find("time")
    if not element:
        return None
    return element.get("datetime") or clean_text(element.get_text(" "))


def extract_meta_keywords(soup: Any) -> list[str]:
    keywords = meta_content(soup, "name", "keywords")
    if not keywords:
        return []
    return [clean_text(keyword) for keyword in keywords.split(",") if clean_text(keyword)]


def extract_main_text(soup: Any, max_chars: int = 8000) -> str:
    container = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = [clean_text(p.get_text(" ")) for p in container.find_all("p")]
    text = "\n".join(paragraph for paragraph in paragraphs if len(paragraph) > 35)
    return text[:max_chars]


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()
