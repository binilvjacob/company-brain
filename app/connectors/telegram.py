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
(redact -> chunk -> embed -> visibility); the buffer/distill/capture core is
shared with every chat connector (app/connectors/common.py — Slack proved the
"same shape" claim). A connector is a client of the Brain, never a second
brain.

Commands: /ask <question> · /teach [n] · /team <ops|product|eng|gtm|ga|meta>
          · /help
"""
import json
import urllib.request
from datetime import datetime, timezone

import psycopg

from app import config
from app.answer import ask
from app.connectors import common
from app.connectors.common import run_ambient_digest  # noqa: F401 — public API
from app.redact import redact

USAGE = (
    "I'm the Company Brain.\n"
    "/ask <question> — cited answer (or an honest refusal, logged as a gap)\n"
    "/teach [n] — save the last n messages (default 20) as vouched knowledge\n"
    "/team <ops|product|eng|gtm|ga|meta> — set which team this chat belongs to\n"
    "Everything else said here is buffered (identifiers redacted on arrival) "
    "and distilled into low-authority chat notes once the conversation goes quiet."
)


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
           WHERE source = 'telegram' AND chat_id = %s AND processed = FALSE
           ORDER BY sent_at DESC LIMIT %s""", (chat_id, n)).fetchall()
    if not rows:
        send(chat_id, "Nothing new to teach — no unprocessed messages in this chat.")
        return
    ko = common.ingest_run(conn, source="telegram", chat_id=chat_id,
                           chat_title=chat_title, rows=list(reversed(rows)),
                           doc_type="notes", owner=user, via="teach")
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
    common.upsert_chat(conn, "telegram", chat_id, chat_title)

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
    common.run_ambient_digest(conn)
