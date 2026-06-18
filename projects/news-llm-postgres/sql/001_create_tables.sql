CREATE TABLE IF NOT EXISTS news_documents (
    id BIGSERIAL PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_documents_payload_gin
    ON news_documents USING GIN (payload);

CREATE INDEX IF NOT EXISTS idx_news_documents_category
    ON news_documents ((payload #>> '{analysis,category}'));

CREATE INDEX IF NOT EXISTS idx_news_documents_source
    ON news_documents ((payload #>> '{source,key}'));

CREATE INDEX IF NOT EXISTS idx_news_documents_published_at
    ON news_documents ((payload #>> '{article,published_at}'));
