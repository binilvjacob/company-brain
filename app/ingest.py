"""Ingest: KnowledgeObject → redact → chunk → embed → index. Idempotent per id."""
import json

import psycopg

from app.chunking import chunk_document
from app.embeddings import embed_texts
from app.models import KnowledgeObject
from app.redact import redact


def ingest_document(conn: psycopg.Connection, ko: KnowledgeObject) -> dict:
    clean_body, redactions = redact(ko.body)
    chunks = chunk_document(ko.title, clean_body)
    vectors = embed_texts([c.embed_text for c in chunks])

    with conn.transaction():
        conn.execute(
            """
            INSERT INTO documents (id, title, body, source_type, source_url, team,
                                   doc_type, owner, updated_at, visibility, entities, provenance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
              title = EXCLUDED.title, body = EXCLUDED.body,
              source_type = EXCLUDED.source_type, source_url = EXCLUDED.source_url,
              team = EXCLUDED.team, doc_type = EXCLUDED.doc_type,
              owner = EXCLUDED.owner, updated_at = EXCLUDED.updated_at,
              visibility = EXCLUDED.visibility, entities = EXCLUDED.entities,
              provenance = EXCLUDED.provenance
            """,
            (ko.id, ko.title, clean_body, ko.source_type, ko.source_url, ko.team,
             ko.doc_type, ko.owner, ko.updated_at, ko.visibility, ko.entities,
             json.dumps(ko.provenance) if ko.provenance else None),
        )
        conn.execute("DELETE FROM chunks WHERE doc_id = %s", (ko.id,))
        for chunk, vec in zip(chunks, vectors):
            conn.execute(
                """
                INSERT INTO chunks (doc_id, ord, heading, text, embed_text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (ko.id, chunk.ord, chunk.heading, chunk.text, chunk.embed_text, str(vec)),
            )

    return {"id": ko.id, "chunks": len(chunks), "redactions": redactions}


def ingest_all(conn: psycopg.Connection, objects: list[KnowledgeObject]) -> dict:
    stats = {"docs": 0, "chunks": 0, "redactions": 0}
    for ko in objects:
        r = ingest_document(conn, ko)
        stats["docs"] += 1
        stats["chunks"] += r["chunks"]
        stats["redactions"] += r["redactions"]
    return stats
