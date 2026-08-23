"""Telegram connector — the first live source. No exports, no uploads.

A bot sits in the team's group chats (standing in for WhatsApp: identical
webhook mechanism, minus Meta's business-verification queue) and the chat
joins the Brain three ways:

- ambient: every message is buffered — PHI-redacted AT THE BOUNDARY, before
  it even touches the buffer table. When a chat goes quiet, the buffered run
  is distilled into ONE low-authority `chat_thread` knowledge object. Raw
  messages never become objects one-by-one: indexing scrollback verbatim is
  how you build a swamp, not a brain.
- vouched: /teach captures the recent run NOW as a higher-authority `notes`
  object with provenance (who taught, which chat, which messages). A human
  vouching at the moment of capture beats any amount of hoovering.
- bidirectional: /ask answers inside the chat with sources, or refuses and
  logs a routed gap — the Brain meets the team where questions already
  happen.

Everything terminates in the same ingest pipeline as every other source
(redact -> chunk -> embed -> visibility). A connector is a client of the
Brain, never a second brain.

Commands: /ask <question> · /teach [n] · /team <ops|product|eng|gtm|ga|meta>
          · /help
"""
import json
import re
import traceback
import urllib.request
from datetime import datetime, timedelta, timezone

import psycopg

from app import config
from app.answer import ask
from app.ingest import ingest_document
from app.llm import generate_json
from app.models import KnowledgeObject
from app.redact import redact

USAGE = (
    "I'm the Company Brain.\n"
    "/ask <question> — cited answer (or an honest refusal, logged as a gap)\n"
    "/teach [n] — save the last n messages (default 20) as vouched knowledge\n"
    "/team <ops|product|eng|gtm|ga|meta> — set which team this chat belongs to\n"
    "Everything else said here is buffered (identifiers redacted on arrival) "
    "and distilled into low-authority chat notes once the conversation goes quiet."
)

DISTILL_PROMPT = """You turn an internal team chat transcript into one reusable
knowledge note. Extract the durable knowledge (rules, decisions, fixes,
gotchas) — not the chit-chat. Return JSON:
{"title": str (specific, <90 chars), "summary_markdown": str (the knowledge,
tight), "entities": [str] (payers, codes, systems, vendors mentioned)}"""


# --------------------------------------------------------------- Telegram API

def enabled() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN)


def _api(method: str, payload: dict) -> dict:
    """Call the Bot API; never raise into the webhook path."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 — a chat reply must never take the app down
        print(f"telegram api {method} failed: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text: str, reply_to=None) -> None:
    payload = {"chat_id": chat_id, "text": text[:3900]}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    _api("sendMessage", payload)


def register_webhook(base_url: str) -> dict:
    """Point the bot at this deployment. Called at app startup on Render
    (RENDER_EXTERNAL_URL is set by the platform), so a deploy with the token
    configured is self-wiring — zero manual steps."""
    resp = _api("setWebhook", {
        "url": f"{base_url}/hooks/telegram",
        "secret_token": config.CONNECTOR_SECRET or "",
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    })
    print(f"telegram: setWebhook -> {resp}")
    return resp


# ------------------------------------------------------------------- helpers

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40]


def _chat_team(conn: psycopg.Connection, chat_id: str) -> str:
    row = conn.execute(
        "SELECT team FROM connector_chats WHERE chat_id = %s", (chat_id,)).fetchone()
    return row["team"] if row else config.TELEGRAM_DEFAULT_TEAM


def _upsert_chat(conn: psycopg.Connection, chat_id: str, title: str) -> None:
    conn.execute(
        """INSERT INTO connector_chats (chat_id, source, title, team)
           VALUES (%s, 'telegram', %s, %s)
           ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title""",
        (chat_id, title, config.TELEGRAM_DEFAULT_TEAM),
    )


def _distill(chat_title: str, lines: list[str]) -> dict:
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


def _ingest_run(conn, *, chat_id: str, chat_title: str, rows: list[dict],
                doc_type: str, owner: str, via: str) -> KnowledgeObject:
    lines = [f"{r['user_name']} ({r['sent_at']:%Y-%m-%d %H:%M}): {r['text']}" for r in rows]
    d = _distill(chat_title, lines)
    last_at = max(r["sent_at"] for r in rows)
    now = datetime.now(timezone.utc)
    ko = KnowledgeObject(
        id=f"tg-{via}-{_slug(chat_id)}-{now:%Y%m%d%H%M%S}",
        title=d["title"],
        body=d["summary_markdown"],
        source_type="telegram",
        source_url=f"telegram://{chat_id}/{rows[0]['msg_id']}",
        team=_chat_team(conn, chat_id),
        doc_type=doc_type,
        owner=owner,
        updated_at=last_at,
        entities=d["entities"],
        provenance={"via": f"telegram-{via}", "chat": chat_title,
                    "captured_by": owner, "captured_at": now.isoformat(),
                    "message_ids": [r["msg_id"] for r in rows]},
    )
    ingest_document(conn, ko)
    conn.execute(
        "UPDATE connector_messages SET processed = TRUE WHERE id = ANY(%s)",
        ([r["id"] for r in rows],),
    )
    return ko


# ------------------------------------------------------------------ commands

def _cmd_ask(conn, chat_id, q: str, send) -> None:
    if not q.strip():
        send(chat_id, "Usage: /ask <question>")
        return
    out = ask(conn, q.strip(), role="everyone")
    if not out["answered"]:
        send(chat_id, f"{out['message']}\n(confidence {out['confidence']})")
        return
    cites = "\n".join(
        f"[{c['n']}] {c['title']} ({c['doc_type']}, {c['updated_at']})"
        for c in out["citations"])
    note = f"\n⚠ {out['staleness_note']}" if out.get("staleness_note") else ""
    send(chat_id, f"{out['answer_markdown']}{note}\n\nSources:\n{cites}")


def _cmd_teach(conn, chat_id, chat_title, user: str, arg: str, send) -> None:
    try:
        n = min(int(arg), 100) if arg.strip() else 20
    except ValueError:
        n = 20
    rows = conn.execute(
        """SELECT * FROM connector_messages
           WHERE chat_id = %s AND processed = FALSE
           ORDER BY sent_at DESC LIMIT %s""", (chat_id, n)).fetchall()
    if not rows:
        send(chat_id, "Nothing new to teach — no unprocessed messages in this chat.")
        return
    ko = _ingest_run(conn, chat_id=chat_id, chat_title=chat_title,
                     rows=list(reversed(rows)), doc_type="notes",
                     owner=user, via="teach")
    send(chat_id, f"Learned: \"{ko.title}\" — {len(rows)} messages captured "
                  f"with provenance. It's citable right now (/ask to check).")


def _cmd_team(conn, chat_id, arg: str, send) -> None:
    team = arg.strip().lower()
    if team not in config.TEAMS:
        send(chat_id, f"Unknown team '{team}'. One of: {', '.join(config.TEAMS)}")
        return
    conn.execute("UPDATE connector_chats SET team = %s WHERE chat_id = %s",
                 (team, chat_id))
    send(chat_id, f"This chat now files knowledge under team '{team}'.")


# ------------------------------------------------------------------ entrypoints

def handle_update(conn: psycopg.Connection, update: dict, send=None) -> None:
    """Process one Telegram update. Commands act; plain text is buffered
    (redacted first); then the ambient digester gets a cheap look."""
    send = send or send_message
    msg = update.get("message") or {}
    text = msg.get("text")
    chat = msg.get("chat") or {}
    if not text or "id" not in chat:
        return
    chat_id = str(chat["id"])
    chat_title = chat.get("title") or chat.get("username") or f"dm-{chat_id}"
    sender = (msg.get("from") or {})
    user = sender.get("username") or sender.get("first_name") or "someone"
    _upsert_chat(conn, chat_id, chat_title)

    if text.startswith("/"):
        head, _, rest = text.partition(" ")
        cmd = head.split("@", 1)[0].lower()
        if cmd == "/ask":
            _cmd_ask(conn, chat_id, rest, send)
        elif cmd == "/teach":
            _cmd_teach(conn, chat_id, chat_title, user, rest, send)
        elif cmd == "/team":
            _cmd_team(conn, chat_id, rest, send)
        elif cmd in ("/help", "/start"):
            send(chat_id, USAGE)
        return  # unknown commands are ignored; commands are never buffered

    clean, _ = redact(text)  # PHI never touches disk, not even the buffer
    sent_at = datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc) \
        if msg.get("date") else datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO connector_messages (source, chat_id, msg_id, user_name, text, sent_at)
           VALUES ('telegram', %s, %s, %s, %s, %s)
           ON CONFLICT (source, chat_id, msg_id) DO NOTHING""",
        (chat_id, str(msg.get("message_id", "")), user, clean, sent_at),
    )
    run_ambient_digest(conn)


def run_ambient_digest(conn: psycopg.Connection) -> int:
    """Distill quiet chats into chat_thread objects. Called after each webhook
    and by POST /sync/run (which the keepwarm cron hits every 10 minutes), so
    ambient capture needs no worker process — free-tier honest."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.DIGEST_QUIET_MINUTES)
    chats = conn.execute(
        """SELECT chat_id, count(*) AS n, max(sent_at) AS last
           FROM connector_messages WHERE processed = FALSE
           GROUP BY chat_id""").fetchall()
    made = 0
    for c in chats:
        if c["n"] < config.DIGEST_MIN_MESSAGES or c["last"] > cutoff:
            continue
        rows = conn.execute(
            """SELECT * FROM connector_messages
               WHERE chat_id = %s AND processed = FALSE ORDER BY sent_at""",
            (c["chat_id"],)).fetchall()
        title_row = conn.execute(
            "SELECT title, team FROM connector_chats WHERE chat_id = %s",
            (c["chat_id"],)).fetchone()
        chat_title = (title_row or {}).get("title") or c["chat_id"]
        owner = config.TEAM_OWNER.get((title_row or {}).get("team") or "ops", "priya")
        try:
            _ingest_run(conn, chat_id=c["chat_id"], chat_title=chat_title,
                        rows=rows, doc_type="chat_thread", owner=owner, via="digest")
            made += 1
        except Exception:  # noqa: BLE001 — one bad chat must not block the rest
            traceback.print_exc()
    return made
