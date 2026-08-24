"""Shared connector machinery: buffer -> distill -> ingest, per-source profile.

Extracted from the Telegram connector the day the second connector (Slack)
arrived — the moment "same shape" stopped being a claim and became a refactor.
Everything here is source-agnostic: connectors own their transport (webhook
auth, outbound replies, platform markup); the buffering, quiet-chat digestion,
and vouched capture live once, keyed by a small per-source profile.
"""
import re
import traceback
from datetime import datetime, timedelta, timezone

import psycopg

from app import config
from app.ingest import ingest_document
from app.llm import generate_json
from app.models import KnowledgeObject

DISTILL_PROMPT = """You turn an internal team chat transcript into one reusable
knowledge note. Extract the durable knowledge (rules, decisions, fixes,
gotchas) — not the chit-chat. Return JSON:
{"title": str (specific, <90 chars), "summary_markdown": str (the knowledge,
tight), "entities": [str] (payers, codes, systems, vendors mentioned)}"""

# What differs between chat sources when a buffered run becomes knowledge:
# the id prefix, the source_type on the document, the URL scheme, the ambient
# doc_type (slack digests file as slack_thread, next to the export adapter's
# threads — same trust tier, same shelf), and the default team for new chats.
PROFILES = {
    "telegram": {
        "prefix": "tg",
        "source_type": "telegram",
        "url_scheme": "telegram",
        "digest_doc_type": "chat_thread",
        "default_team": lambda: config.TELEGRAM_DEFAULT_TEAM,
    },
    "slack": {
        "prefix": "sl",
        "source_type": "slack",
        "url_scheme": "slack",
        "digest_doc_type": "slack_thread",
        "default_team": lambda: config.SLACK_DEFAULT_TEAM,
    },
}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40]


def chat_team(conn: psycopg.Connection, source: str, chat_id: str) -> str:
    row = conn.execute(
        "SELECT team FROM connector_chats WHERE chat_id = %s", (chat_id,)).fetchone()
    return row["team"] if row else PROFILES[source]["default_team"]()


def upsert_chat(conn: psycopg.Connection, source: str, chat_id: str,
                title: str | None) -> None:
    """Register/refresh a chat. A None title never clobbers a known one —
    Slack message events carry only the channel id; the name arrives later
    with the first slash command."""
    conn.execute(
        """INSERT INTO connector_chats (chat_id, source, title, team)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (chat_id) DO UPDATE
           SET title = COALESCE(EXCLUDED.title, connector_chats.title)""",
        (chat_id, source, title, PROFILES[source]["default_team"]()),
    )


def distill(chat_title: str, lines: list[str]) -> dict:
    transcript = "\n".join(lines)[:12000]
    if config.LLM_PROVIDER == "mock":
        # Deterministic offline behaviour, mirroring the adapters' spirit.
        return {"title": f"Chat notes: {chat_title}",
                "summary_markdown": transcript, "entities": []}
    resp = generate_json(DISTILL_PROMPT, f"Chat: {chat_title}\n\nTranscript:\n{transcript}")
    title = (resp.get("title") or f"Chat notes: {chat_title}")[:120]
    summary = resp.get("summary_markdown") or transcript
    body = f"{summary}\n\n---\nSource transcript (redacted at capture):\n{transcript}"
    return {"title": title, "summary_markdown": body,
            "entities": [str(e) for e in (resp.get("entities") or [])][:12]}


def ingest_run(conn, *, source: str, chat_id: str, chat_title: str,
               rows: list[dict], doc_type: str, owner: str, via: str) -> KnowledgeObject:
    """Distill one run of buffered messages into a knowledge object and mark
    the messages processed. `via` is 'teach' or 'digest'."""
    p = PROFILES[source]
    lines = [f"{r['user_name']} ({r['sent_at']:%Y-%m-%d %H:%M}): {r['text']}" for r in rows]
    d = distill(chat_title, lines)
    last_at = max(r["sent_at"] for r in rows)
    now = datetime.now(timezone.utc)
    ko = KnowledgeObject(
        id=f"{p['prefix']}-{via}-{slug(chat_id)}-{now:%Y%m%d%H%M%S}",
        title=d["title"],
        body=d["summary_markdown"],
        source_type=p["source_type"],
        source_url=f"{p['url_scheme']}://{chat_id}/{rows[0]['msg_id']}",
        team=chat_team(conn, source, chat_id),
        doc_type=doc_type,
        owner=owner,
        updated_at=last_at,
        entities=d["entities"],
        provenance={"via": f"{p['source_type']}-{via}", "chat": chat_title,
                    "captured_by": owner, "captured_at": now.isoformat(),
                    "message_ids": [r["msg_id"] for r in rows]},
    )
    ingest_document(conn, ko)
    conn.execute(
        "UPDATE connector_messages SET processed = TRUE WHERE id = ANY(%s)",
        ([r["id"] for r in rows],),
    )
    return ko


def run_ambient_digest(conn: psycopg.Connection) -> int:
    """Distill quiet chats into low-authority knowledge objects, whatever the
    source. Called after each inbound message and by POST /sync/run (which the
    keepwarm cron hits every 10 minutes), so ambient capture needs no worker
    process — free-tier honest."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.DIGEST_QUIET_MINUTES)
    chats = conn.execute(
        """SELECT source, chat_id, count(*) AS n, max(sent_at) AS last
           FROM connector_messages WHERE processed = FALSE
           GROUP BY source, chat_id""").fetchall()
    made = 0
    for c in chats:
        if c["n"] < config.DIGEST_MIN_MESSAGES or c["last"] > cutoff:
            continue
        p = PROFILES.get(c["source"])
        if not p:
            continue
        rows = conn.execute(
            """SELECT * FROM connector_messages
               WHERE source = %s AND chat_id = %s AND processed = FALSE
               ORDER BY sent_at""",
            (c["source"], c["chat_id"])).fetchall()
        title_row = conn.execute(
            "SELECT title, team FROM connector_chats WHERE chat_id = %s",
            (c["chat_id"],)).fetchone()
        chat_title = (title_row or {}).get("title") or c["chat_id"]
        owner = config.TEAM_OWNER.get((title_row or {}).get("team") or "ops", "priya")
        try:
            ingest_run(conn, source=c["source"], chat_id=c["chat_id"],
                       chat_title=chat_title, rows=rows,
                       doc_type=p["digest_doc_type"], owner=owner, via="digest")
            made += 1
        except Exception:  # noqa: BLE001 — one bad chat must not block the rest
            traceback.print_exc()
    return made
