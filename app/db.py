"""One Postgres for everything: rows, full-text (tsvector), vectors (pgvector)."""
import psycopg
from psycopg.rows import dict_row

from app import config

_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  body        TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_url  TEXT,
  team        TEXT NOT NULL,
  doc_type    TEXT NOT NULL,
  owner       TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL,
  visibility  TEXT[] NOT NULL DEFAULT '{everyone}',
  entities    TEXT[] NOT NULL DEFAULT '{}',
  provenance  JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id         BIGSERIAL PRIMARY KEY,
  doc_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ord        INT NOT NULL,
  heading    TEXT,
  text       TEXT NOT NULL,
  embed_text TEXT NOT NULL,
  tsv        tsvector GENERATED ALWAYS AS (to_tsvector('english', embed_text)) STORED,
  embedding  vector(%(dim)s)
);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_doc_idx ON chunks (doc_id);

CREATE TABLE IF NOT EXISTS gaps (
  id            BIGSERIAL PRIMARY KEY,
  question      TEXT NOT NULL,
  normalized    TEXT NOT NULL UNIQUE,
  asked_by_role TEXT,
  routed_owner  TEXT,
  team_guess    TEXT,
  count         INT NOT NULL DEFAULT 1,
  status        TEXT NOT NULL DEFAULT 'open',
  source        TEXT NOT NULL DEFAULT 'live',
  first_asked   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_asked    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recipes (
  slug        TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  description TEXT DEFAULT '',
  inputs      JSONB NOT NULL,
  retrieval   JSONB NOT NULL,
  prompt      TEXT NOT NULL,
  output      TEXT NOT NULL DEFAULT 'card',
  created_by  TEXT NOT NULL DEFAULT 'system',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS captures (
  id          BIGSERIAL PRIMARY KEY,
  doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  captured_by TEXT,
  case_ref    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS query_log (
  id         BIGSERIAL PRIMARY KEY,
  q          TEXT NOT NULL,
  role       TEXT,
  answered   BOOLEAN,
  latency_ms INT,
  cost_usd   NUMERIC(10, 6) DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def connect() -> psycopg.Connection:
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=True)


def init_schema(conn: psycopg.Connection) -> None:
    conn.execute(_SCHEMA % {"dim": config.EMBEDDING_DIM})
    # HNSW needs pgvector >= 0.5; fall back to exact scan (corpus is small) if absent.
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks "
            "USING hnsw (embedding vector_cosine_ops)"
        )
    except psycopg.Error:
        pass


def counts(conn: psycopg.Connection) -> dict:
    row = conn.execute(
        "SELECT (SELECT count(*) FROM documents) AS docs, (SELECT count(*) FROM chunks) AS chunks"
    ).fetchone()
    return {"docs": row["docs"], "chunks": row["chunks"]}
