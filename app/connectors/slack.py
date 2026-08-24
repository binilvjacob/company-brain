"""Slack connector — the second live source, and the proof of "same shape".

The writeup's cut-list said live Slack was "scope, not design": the Events API
is the same webhook mechanism as Telegram's. This file is that claim cashed
in — transport differs (HMAC request signing instead of a secret header, a
one-time URL challenge, a 3-second ack budget on slash commands), while the
brain of it (buffer -> quiet-window digest -> vouched capture) is the shared
core in app/connectors/common.py.

Two platform notes that make live-first the *only* honest Slack design:

- Since May 2025, new non-Marketplace apps get `conversations.history` at
  1 request/minute, 15 messages a call. Export-then-index is dead on arrival;
  knowledge has to be captured as it is said. This connector never calls the
  history API at all — what it missed while dark stays missed, by design.
- A single-workspace install issues its bot token from the app dashboard —
  no OAuth flow, same trust posture as Telegram's BotFather token. OAuth is
  what multi-tenant distribution costs, which is a product decision, not a
  take-home decision.

Ambient digests file as `slack_thread` — the same shelf and trust tier (0.6)
as the v1 Slack-export adapter's threads. The adapter proved the shape on
files; this removes the files.

Commands: /ask <question> · /teach [n] · /team <ops|product|eng|gtm|ga|meta>
Mention:  @Company Brain <question> — answers in-thread with citations.
"""
import hashlib
import hmac
import html
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from typing import Callable

import psycopg

from app import config
from app.answer import ask
from app.connectors import common
from app.redact import redact

USAGE = (
    "I'm the Company Brain.\n"
    "/ask <question> — cited answer (or an honest refusal, logged as a gap)\n"
    "/teach [n] — save the last n messages (default 20) as vouched knowledge\n"
    "/team <ops|product|eng|gtm|ga|meta> — set which team this channel belongs to\n"
    "Or just @-mention me with a question. Everything else said here is "
    "buffered (identifiers redacted on arrival) and distilled into "
    "low-authority chat notes once the channel goes quiet."
)


def enabled() -> bool:
    return bool(config.SLACK_BOT_TOKEN and config.SLACK_SIGNING_SECRET)


# -------------------------------------------------------------- Slack Web API

def _api(method: str, payload: dict) -> dict:
    """Call the Slack Web API; never raise into the webhook path."""
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Authorization": f"Bearer {config.SLACK_BOT_TOKEN}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 — a chat reply must never take the app down
        print(f"slack api {method} failed: {e}")
        return {"ok": False, "error": str(e)}


def post_message(channel: str, text: str, thread_ts: str | None = None) -> None:
    payload = {"channel": channel, "text": text[:3900]}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    _api("chat.postMessage", payload)


def post_response(response_url: str, text: str, in_channel: bool = True) -> None:
    """Reply to a slash command via its response_url (valid ~30 min, no auth)."""
    body = {"response_type": "in_channel" if in_channel else "ephemeral",
            "text": text[:3900]}
    req = urllib.request.Request(
        response_url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:  # noqa: BLE001
        print(f"slack response_url post failed: {e}")


_bot_user_id: str | None = None       # resolved lazily via auth.test
_user_names: dict[str, str] = {}      # user id -> display name cache


def bot_user_id() -> str:
    global _bot_user_id
    if _bot_user_id is None:
        resp = _api("auth.test", {})
        _bot_user_id = resp.get("user_id") or "" if resp.get("ok") else ""
    return _bot_user_id


def display_name(user_id: str) -> str:
    if not user_id:
        return "someone"
    if user_id not in _user_names:
        resp = _api("users.info", {"user": user_id})
        prof = (resp.get("user") or {}).get("profile") or {} if resp.get("ok") else {}
        _user_names[user_id] = (prof.get("display_name")
                                or prof.get("real_name")
                                or (resp.get("user") or {}).get("name")
                                or user_id)
    return _user_names[user_id]


# ----------------------------------------------------------- request signing

def verify_signature(timestamp: str, signature: str, body: bytes) -> bool:
    """Slack signs every request: v0=HMAC_SHA256(secret, "v0:{ts}:{body}").
    The ±5-minute timestamp window closes replay; compare_digest closes
    timing. Same fail-closed posture as the Telegram secret header."""
    if not config.SLACK_SIGNING_SECRET:
        return False
    try:
        if abs(time.time() - int(float(timestamp))) > 300:
            return False
    except (TypeError, ValueError):
        return False
    base = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(config.SLACK_SIGNING_SECRET.encode(),
                                base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


# ------------------------------------------------------- Slack markup -> text

_MENTION = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]*)?>")
_CHANNEL = re.compile(r"<#[A-Z0-9]+\|([^>]*)>")
_LINK = re.compile(r"<(https?://[^|>]+)(?:\|([^>]*))?>")


def clean_text(text: str) -> str:
    """Normalize Slack markup before anything is stored or distilled: a digest
    full of <@U0A1B2> and <https://x|x> embeds badly and reads worse."""
    text = _MENTION.sub(lambda m: f"@{display_name(m.group(1))}", text)
    text = _CHANNEL.sub(lambda m: f"#{m.group(1)}", text)
    text = _LINK.sub(lambda m: m.group(2) or m.group(1), text)
    return html.unescape(text)


def _answer_text(out: dict) -> str:
    if not out["answered"]:
        return f"{out['message']}\n(confidence {out['confidence']})"
    cites = "\n".join(
        f"[{c['n']}] {c['title']} ({c['doc_type']}, {c['updated_at']})"
        for c in out["citations"])
    note = f"\n⚠ {out['staleness_note']}" if out.get("staleness_note") else ""
    return f"{out['answer_markdown']}{note}\n\nSources:\n{cites}"


# ------------------------------------------------------------- Events API

def handle_event(conn: psycopg.Connection, payload: dict) -> None:
    """Process one event_callback. Mentions answer; plain channel talk is
    buffered (redacted first); then the ambient digester gets a cheap look.
    Slack redelivers unacked events — the (source, chat_id, msg_id=ts) unique
    key makes retries idempotent."""
    event = payload.get("event") or {}
    etype = event.get("type")

    if etype == "app_mention":
        _handle_mention(conn, event)
        return
    if etype != "message":
        return
    if event.get("bot_id") or event.get("subtype"):
        return  # our own posts, other bots, edits/joins: never buffered
    text, channel = event.get("text"), event.get("channel")
    if not text or not channel:
        return
    me = bot_user_id()
    if me and f"<@{me}>" in text:
        return  # delivered again as app_mention — answered there, not buffered

    common.upsert_chat(conn, "slack", channel, None)
    clean, _ = redact(clean_text(text))  # PHI never touches disk, not even the buffer
    ts = event.get("ts") or ""
    sent_at = datetime.fromtimestamp(float(ts), tz=timezone.utc) \
        if ts else datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO connector_messages (source, chat_id, msg_id, user_name, text, sent_at)
           VALUES ('slack', %s, %s, %s, %s, %s)
           ON CONFLICT (source, chat_id, msg_id) DO NOTHING""",
        (channel, ts, display_name(event.get("user") or ""), clean, sent_at),
    )
    common.run_ambient_digest(conn)


def _handle_mention(conn, event: dict) -> None:
    channel = event.get("channel") or ""
    thread = event.get("thread_ts") or event.get("ts")
    q = _MENTION.sub("", event.get("text") or "").strip()
    common.upsert_chat(conn, "slack", channel, None)
    if not q:
        post_message(channel, USAGE, thread_ts=thread)
        return
    post_message(channel, _answer_text(ask(conn, clean_text(q), role="everyone")),
                 thread_ts=thread)


# ---------------------------------------------------------- slash commands

def _ack(text: str, in_channel: bool = False) -> dict:
    return {"response_type": "in_channel" if in_channel else "ephemeral",
            "text": text}


def handle_command(conn: psycopg.Connection,
                   form: dict) -> tuple[dict, Callable | None]:
    """Route one slash command. Returns (immediate ack, deferred work) — Slack
    voids commands unanswered in 3 seconds, and /ask's p50 alone is ~2s, so
    anything that thinks acks first and delivers through response_url."""
    cmd = (form.get("command") or "").strip()
    text = (form.get("text") or "").strip()
    channel = form.get("channel_id") or ""
    common.upsert_chat(conn, "slack", channel, form.get("channel_name") or None)

    if cmd == "/ask":
        if not text:
            return _ack("Usage: /ask <question>"), None
        return (_ack(f"Asking the Brain: _{text[:120]}_ …"),
                lambda c: run_ask(c, form))
    if cmd == "/teach":
        return (_ack("Capturing this channel's recent messages…"),
                lambda c: run_teach(c, form))
    if cmd == "/team":
        team = text.lower()
        if team not in config.TEAMS:
            return _ack(f"Unknown team '{team}'. One of: {', '.join(config.TEAMS)}"), None
        conn.execute("UPDATE connector_chats SET team = %s WHERE chat_id = %s",
                     (team, channel))
        return _ack(f"This channel now files knowledge under team '{team}'.",
                    in_channel=True), None
    return _ack(USAGE), None


def run_ask(conn: psycopg.Connection, form: dict) -> None:
    q = clean_text((form.get("text") or "").strip())
    out = ask(conn, q, role="everyone")
    post_response(form.get("response_url") or "",
                  f"*/ask* {q}\n\n{_answer_text(out)}", in_channel=True)


def run_teach(conn: psycopg.Connection, form: dict) -> None:
    arg = (form.get("text") or "").strip()
    try:
        n = min(int(arg), 100) if arg else 20
    except ValueError:
        n = 20
    channel = form.get("channel_id") or ""
    user = form.get("user_name") or form.get("user_id") or "someone"
    rows = conn.execute(
        """SELECT * FROM connector_messages
           WHERE source = 'slack' AND chat_id = %s AND processed = FALSE
           ORDER BY sent_at DESC LIMIT %s""", (channel, n)).fetchall()
    url = form.get("response_url") or ""
    if not rows:
        post_response(url, "Nothing new to teach — no unprocessed messages "
                           "in this channel.", in_channel=False)
        return
    title = form.get("channel_name") or channel
    ko = common.ingest_run(conn, source="slack", chat_id=channel,
                           chat_title=f"#{title}", rows=list(reversed(rows)),
                           doc_type="notes", owner=user, via="teach")
    post_response(url, f"Learned: \"{ko.title}\" — {len(rows)} messages captured "
                       f"with provenance. It's citable right now (/ask to check).",
                  in_channel=True)
