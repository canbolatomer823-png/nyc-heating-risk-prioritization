from __future__ import annotations

from pathlib import Path
from typing import Any


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_schema(self) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required. Run `pip install -r requirements.txt`.") from exc

        sql_path = Path(__file__).resolve().parents[2] / "sql" / "001_create_tables.sql"
        schema_sql = sql_path.read_text(encoding="utf-8")
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)

    def upsert_payloads(self, payloads: list[dict[str, Any]]) -> int:
        if not payloads:
            return 0

        try:
            import psycopg
            from psycopg.types.json import Jsonb
        except ImportError as exc:
            raise RuntimeError("psycopg is required. Run `pip install -r requirements.txt`.") from exc

        sql = """
            INSERT INTO news_documents (content_hash, payload)
            VALUES (%s, %s)
            ON CONFLICT (content_hash)
            DO UPDATE SET
                payload = EXCLUDED.payload,
                collected_at = now()
        """

        rows = [
            (payload["pipeline"]["content_hash"], Jsonb(payload))
            for payload in payloads
        ]
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)
        return len(rows)
