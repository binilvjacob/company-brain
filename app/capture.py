"""The capture loop — the strategic core.

Specialists generate high-value knowledge hourly: every resolved exception is a
judgment call encoded with domain expertise, and today it evaporates when the
ticket closes. "Teach the Brain" is one click: the resolution becomes a
KnowledgeObject with provenance (who, when, which case), is redacted, chunked,
embedded, and is retrievable by the next specialist — and eventually by the
verification agents themselves. This is how 85% straight-through becomes 92%
without retraining a model.
"""
import re
from datetime import datetime, timezone

import psycopg

from app.ingest import ingest_document
from app.models import KnowledgeObject


def teach(conn: psycopg.Connection, *, payer: str, procedure: str, flag_reason: str,
          decision: str, reasoning: str, author: str, case_ref: str = "") -> dict:
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{payer}-{procedure}-{flag_reason}".lower()).strip("-")[:60]
    doc_id = f"capture-{now:%Y%m%d%H%M%S}-{slug}"
    body = (
        f"Payer: {payer}\nProcedure: {procedure}\nFlag reason: {flag_reason}\n\n"
        f"Decision: {decision}\n\nSpecialist reasoning: {reasoning}"
    )
    ko = KnowledgeObject(
        id=doc_id,
        title=f"Captured resolution: {payer} {procedure} — {flag_reason}",
        body=body,
        source_type="capture",
        source_url=f"brain://captures/{doc_id}",
        team="ops",
        doc_type="resolution",
        owner=author,
        updated_at=now,
        entities=[payer, procedure],
        provenance={"captured_by": author, "captured_at": now.isoformat(),
                    "case_ref": case_ref, "via": "teach-the-brain"},
    )
    result = ingest_document(conn, ko)
    conn.execute(
        "INSERT INTO captures (doc_id, captured_by, case_ref) VALUES (%s, %s, %s)",
        (doc_id, author, case_ref),
    )
    # Close the loop on any open gap this capture plausibly answers.
    conn.execute(
        """
        UPDATE gaps SET status = 'answered'
        WHERE status = 'open' AND (question ILIKE '%%' || %s || '%%')
        """,
        (payer,),
    )
    return {"doc_id": doc_id, **result}


def list_gaps(conn: psycopg.Connection) -> list[dict]:
    return conn.execute(
        "SELECT * FROM gaps ORDER BY (status = 'open') DESC, count DESC, last_asked DESC"
    ).fetchall()
