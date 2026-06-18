from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .fetchers import fetch_article_text, fetch_rss_items
from .llm import get_analyzer
from .models import AnalysisResult, RawNewsItem
from .sources import load_sources
from .storage import PostgresStore


def run_pipeline(
    sources_path: str,
    limit_per_source: int,
    analyzer_name: str,
    output_path: str,
    write_db: bool = False,
    database_url: str | None = None,
    fetch_articles: bool = False,
) -> dict[str, Any]:
    sources = load_sources(sources_path)
    analyzer = get_analyzer(analyzer_name)
    payloads: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for source in sources:
        try:
            items = fetch_rss_items(source, limit=limit_per_source)
        except Exception as exc:
            errors.append({"source": source.key, "stage": "rss_fetch", "error": str(exc)})
            continue

        for item in items:
            if fetch_articles or source.fetch_article:
                try:
                    item = RawNewsItem(
                        **{
                            **asdict(item),
                            "source": item.source,
                            "content_text": fetch_article_text(item.url),
                        }
                    )
                except Exception as exc:
                    item = RawNewsItem(
                        **{
                            **asdict(item),
                            "source": item.source,
                            "raw": {
                                **item.raw,
                                "article_fetch_error": f"{type(exc).__name__}: {exc}",
                            },
                        }
                    )

            analysis = analyzer.analyze(item)
            payloads.append(build_payload(item, analysis))

    write_jsonl(output_path, payloads)

    inserted = 0
    if write_db:
        if not database_url:
            raise ValueError("DATABASE_URL is required when write_db=True")
        store = PostgresStore(database_url)
        store.ensure_schema()
        inserted = store.upsert_payloads(payloads)

    return {
        "sources_enabled": len(sources),
        "payloads": len(payloads),
        "db_upserts": inserted,
        "errors": errors,
        "output_path": output_path,
    }


def build_payload(item: RawNewsItem, analysis: AnalysisResult) -> dict[str, Any]:
    content_hash = content_hash_for_item(item)
    return {
        "schema_version": "news-item-v1",
        "source": {
            "key": item.source.key,
            "name": item.source.name,
            "homepage": item.source.homepage,
            "feed_url": item.source.feed_url,
            "language": item.source.language,
        },
        "article": {
            "title": item.title,
            "url": item.url,
            "summary": item.summary,
            "published_at": item.published_at,
            "author": item.author,
            "tags": item.tags,
            "content_text": item.content_text,
        },
        "analysis": asdict(analysis),
        "scrape": {
            "raw_feed_entry": item.raw,
        },
        "pipeline": {
            "collected_at": utc_now_iso(),
            "content_hash": content_hash,
        },
    }


def content_hash_for_item(item: RawNewsItem) -> str:
    stable_key = f"{item.source.key}|{item.url}".encode("utf-8")
    return hashlib.sha256(stable_key).hexdigest()


def write_jsonl(path: str, payloads: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for payload in payloads:
            file.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
