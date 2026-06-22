from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NewsSource:
    key: str
    name: str
    homepage: str
    source_type: str = "html"
    crawl_url: str | None = None
    allowed_domains: list[str] = field(default_factory=list)
    article_url_patterns: list[str] = field(default_factory=list)
    exclude_url_patterns: list[str] = field(default_factory=list)
    search_query: str | None = None
    language: str = "tr"
    enabled: bool = True
    fetch_article: bool = True


@dataclass(frozen=True)
class RawNewsItem:
    source: NewsSource
    title: str
    url: str
    summary: str = ""
    published_at: str | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    content_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisResult:
    category: str
    subcategory: str
    sentiment: str
    summary: str
    keywords: list[str]
    confidence: float
    analyzer: str
    model: str | None = None
    topics: list[str] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)
    event_type: str = "general"
    geography: list[str] = field(default_factory=list)
    importance: str = "normal"
    risk_flags: list[str] = field(default_factory=list)
    language: str = "tr"
    analysis_version: str = "v2"
    error: str | None = None
