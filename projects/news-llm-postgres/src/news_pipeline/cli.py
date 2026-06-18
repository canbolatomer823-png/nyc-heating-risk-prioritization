from __future__ import annotations

import argparse
import json
import os

from .pipeline import run_pipeline
from .storage import PostgresStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect news, analyze with LLM, store JSONB in Postgres.")
    parser.add_argument("--sources", default="config/sources.json", help="Path to source config JSON.")
    parser.add_argument("--limit-per-source", type=int, default=3, help="Max RSS items per source.")
    parser.add_argument(
        "--analyzer",
        choices=["auto", "openai", "fallback"],
        default="auto",
        help="Analyzer backend. auto uses OpenAI when OPENAI_API_KEY exists, otherwise fallback rules.",
    )
    parser.add_argument("--output", default="outputs/latest_payloads.jsonl", help="JSONL output path.")
    parser.add_argument("--write-db", action="store_true", help="Upsert payloads into Postgres.")
    parser.add_argument("--fetch-articles", action="store_true", help="Fetch article HTML and extract paragraph text.")
    parser.add_argument("--init-db", action="store_true", help="Create Postgres table and indexes, then exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL")

    if args.init_db:
        if not database_url:
            raise SystemExit("DATABASE_URL is required for --init-db")
        PostgresStore(database_url).ensure_schema()
        print(json.dumps({"status": "ok", "action": "init_db"}, ensure_ascii=False))
        return

    summary = run_pipeline(
        sources_path=args.sources,
        limit_per_source=args.limit_per_source,
        analyzer_name=args.analyzer,
        output_path=args.output,
        write_db=args.write_db,
        database_url=database_url,
        fetch_articles=args.fetch_articles,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
