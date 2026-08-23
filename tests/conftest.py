import os

# Must be set before any app import: config reads env at import time.
os.environ["EMBEDDINGS_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["CONFIDENCE_THRESHOLD"] = "0.12"  # mock BoW cosine runs lower than real embeddings
os.environ.setdefault(
    "DATABASE_URL", "postgresql://brain:brain@127.0.0.1:5432/brain_test"
)

from datetime import datetime, timedelta, timezone  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402

from app import db  # noqa: E402
from app.models import KnowledgeObject  # noqa: E402

ADMIN_URL = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/brain"


@pytest.fixture(scope="session")
def conn():
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'brain_test'"
        ).fetchone()
        if not exists:
            admin.execute("CREATE DATABASE brain_test")
    c = db.connect()
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def clean(conn):
    conn.execute("TRUNCATE documents, gaps, recipes, query_log, "
                 "connector_messages, connector_chats CASCADE")
    yield


NOW = datetime.now(timezone.utc)


def ko(id: str, title: str, body: str, *, team="ops", doc_type="playbook",
       owner="priya", days_old=10, visibility=None) -> KnowledgeObject:
    return KnowledgeObject(
        id=id, title=title, body=body, source_type="markdown",
        team=team, doc_type=doc_type, owner=owner,
        updated_at=NOW - timedelta(days=days_old),
        visibility=visibility or ["everyone"],
    )


@pytest.fixture
def seeded(conn):
    """A tiny corpus with the contradiction, a restricted doc, and a decoy."""
    from app.ingest import ingest_all

    fresh_playbook = ko(
        "ddca-playbook", "Delta Dental of California Payer Playbook",
        "## Frequency limitations\n"
        "Effective May 2026, D4910 perio maintenance is limited to 4 per 12 months "
        "following SRP and no longer shares a frequency bucket with D1110 prophylaxis. "
        "D1110 prophylaxis remains 2 per calendar year.",
        doc_type="playbook", days_old=15,
    )
    stale_sop = ko(
        "exception-sop", "Exception Queue SOP",
        "## Frequency limitations example\n"
        "For Delta Dental of California, D4910 perio maintenance counts against the "
        "D1110 prophylaxis frequency bucket: 2 combined per calendar year.",
        doc_type="sop", days_old=250,
    )
    comp = ko(
        "comp-bands", "Compensation Bands FY2026",
        "## Specialist bands\nRCM Specialist L1 compensation band is 6-8 LPA.",
        team="ga", doc_type="policy", owner="maya",
        visibility=["leadership"], days_old=30,
    )
    decoy = ko(
        "voice-runbook", "Voice Agent Runbook",
        "## IVR traversal\nThe voice agent prefers DTMF traversal over speech when an "
        "IVR map exists for the payer.",
        team="eng", doc_type="runbook", owner="nakul", days_old=5,
    )
    resolution = ko(
        "resolution-ex-1001", "Resolved exception EX-1001: Cigna D4910 frequency mismatch",
        "Payer: Cigna\nProcedure: D4910\nFlag reason: frequency history conflict\n"
        "Decision: verified eligible under perio history exception.\n"
        "Specialist reasoning: member has documented perio history, so 4 per year applies.",
        doc_type="resolution", owner="marcus", days_old=40,
    )
    ingest_all(conn, [fresh_playbook, stale_sop, comp, decoy, resolution])
    return conn
