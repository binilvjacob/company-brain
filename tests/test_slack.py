"""Slack connector tests: request signing, the url_verification liveness
probe, boundary redaction + markup normalization, mention answers, the
ack-then-response_url slash flow, /teach provenance, /team routing, and the
per-source digest profiles of the shared connector core. Mock providers, real
Postgres — same posture as the rest of the suite."""
import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import app
from app.capture import list_gaps
from app.connectors import slack as sl
from app.connectors import telegram as tg
from app.retrieval import search

SECRET = "slack-signing-secret"
_TS = iter(range(10_000))


def ts(offset_s: float = 0) -> str:
    """A unique, strictly increasing Slack message ts near now (+offset)."""
    return f"{time.time() + offset_s:.4f}{next(_TS):02d}"


def sign(raw: bytes, req_ts: str) -> str:
    return "v0=" + hmac.new(SECRET.encode(), f"v0:{req_ts}:".encode() + raw,
                            hashlib.sha256).hexdigest()


def post_signed(c, path, body, req_ts=None, secret_ok=True):
    raw = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
    req_ts = req_ts or str(int(time.time()))
    sig = sign(raw, req_ts) if secret_ok else "v0=deadbeef"
    ctype = "application/json" if isinstance(body, dict) \
        else "application/x-www-form-urlencoded"
    return c.post(path, content=raw, headers={
        "content-type": ctype,
        "x-slack-request-timestamp": req_ts,
        "x-slack-signature": sig,
    })


def ev(text, channel="C42WAR", user="U7", msg_ts=None, **extra):
    return {"type": "event_callback", "event": {
        "type": "message", "text": text, "channel": channel,
        "user": user, "ts": msg_ts or ts(), **extra}}


def cmd_body(command, text="", channel="C42WAR", channel_name="ops-war-room",
             user_name="marcus"):
    return urllib.parse.urlencode({
        "command": command, "text": text, "channel_id": channel,
        "channel_name": channel_name, "user_name": user_name,
        "response_url": "https://hooks.slack.test/respond/xyz",
    })


@pytest.fixture
def wired(monkeypatch):
    """Enable the connector, capture outbound traffic, pin identity lookups."""
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setattr(config, "SLACK_SIGNING_SECRET", SECRET)
    monkeypatch.setattr(config, "CONNECTOR_SECRET", "shh-secret")
    monkeypatch.setattr(sl, "_bot_user_id", "UBRAIN")
    monkeypatch.setattr(sl, "_user_names", {"U7": "marcus", "U8": "priya"})
    out = {"messages": [], "responses": []}
    monkeypatch.setattr(sl, "post_message",
                        lambda channel, text, thread_ts=None:
                        out["messages"].append((channel, text, thread_ts)))
    monkeypatch.setattr(sl, "post_response",
                        lambda url, text, in_channel=True:
                        out["responses"].append((url, text, in_channel)))
    return out


def client(seeded):
    app.state.conn = seeded
    return TestClient(app)


def test_signature_challenge_and_disabled_states(seeded, wired, monkeypatch):
    c = client(seeded)
    body = ev("hello")
    assert c.post("/hooks/slack", json=body).status_code == 403          # unsigned
    assert post_signed(c, "/hooks/slack", body, secret_ok=False).status_code == 403
    stale = str(int(time.time()) - 3600)
    assert post_signed(c, "/hooks/slack", body, req_ts=stale).status_code == 403
    assert post_signed(c, "/hooks/slack", body).status_code == 200       # signed

    # url_verification echoes with no signature — the manifest liveness probe —
    # configured or dark.
    probe = {"type": "url_verification", "challenge": "chal-123"}
    assert c.post("/hooks/slack", json=probe).json() == {"challenge": "chal-123"}
    assert c.get("/healthz").json()["connectors"]["slack"] is True
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "")
    assert c.post("/hooks/slack", json=probe).json() == {"challenge": "chal-123"}
    assert c.post("/hooks/slack", json=ev("hi")).status_code == 503
    assert c.get("/healthz").json()["connectors"]["slack"] is False


def test_messages_buffered_redacted_normalized_deduped(seeded, wired):
    c = client(seeded)
    m = ev("&lt;heads up&gt; <@U8> — Member ID: ABC1234567, DOB: 04/12/1985 — "
           "DDCA rule is 2 per year, see <https://portal.example|the portal>")
    assert post_signed(c, "/hooks/slack", m).status_code == 200
    assert post_signed(c, "/hooks/slack", m).status_code == 200  # redelivery
    rows = seeded.execute(
        "SELECT * FROM connector_messages WHERE source = 'slack'").fetchall()
    assert len(rows) == 1                                   # deduped on (chat, ts)
    row = rows[0]
    assert "ABC1234567" not in row["text"] and "04/12/1985" not in row["text"]
    assert "2 per year" in row["text"]
    assert "@priya" in row["text"] and "<@U8>" not in row["text"]   # markup → names
    assert "the portal" in row["text"] and "<https" not in row["text"]
    assert "<heads up>" in row["text"]                       # entities unescaped
    assert row["user_name"] == "marcus"

    # Never buffered: other bots, subtyped events, and mentions of the Brain
    # (those arrive again as app_mention and are answered there).
    post_signed(c, "/hooks/slack", ev("automated noise", bot_id="B99"))
    post_signed(c, "/hooks/slack", ev("edited text", subtype="message_changed"))
    post_signed(c, "/hooks/slack", ev("<@UBRAIN> what is DDCA?"))
    n = seeded.execute(
        "SELECT count(*) AS n FROM connector_messages WHERE source = 'slack'").fetchone()
    assert n["n"] == 1
    assert wired["messages"] == [] and wired["responses"] == []  # buffering is silent


def test_mention_answers_in_thread_with_citations(seeded, wired):
    c = client(seeded)
    q_ts = ts()
    mention = {"type": "event_callback", "event": {
        "type": "app_mention", "channel": "C42WAR", "user": "U7", "ts": q_ts,
        "text": "<@UBRAIN> What is the D4910 frequency rule for Delta Dental of California?"}}
    assert post_signed(c, "/hooks/slack", mention).status_code == 200
    assert len(wired["messages"]) == 1
    channel, text, thread_ts = wired["messages"][0]
    assert channel == "C42WAR" and thread_ts == q_ts
    assert "Sources:" in text and "Delta Dental of California" in text

    bare = {"type": "event_callback", "event": {
        "type": "app_mention", "channel": "C42WAR", "user": "U7", "ts": ts(),
        "text": "<@UBRAIN>"}}
    post_signed(c, "/hooks/slack", bare)
    assert "/ask" in wired["messages"][-1][1]                # usage reply


def test_slash_ask_acks_then_answers_via_response_url(seeded, wired):
    c = client(seeded)
    r = post_signed(c, "/hooks/slack/commands",
                    cmd_body("/ask", "What is the D4910 frequency rule for "
                                     "Delta Dental of California?"))
    assert r.status_code == 200
    assert r.json()["response_type"] == "ephemeral"          # instant ack, <3s
    assert "Asking" in r.json()["text"]
    url, text, in_channel = wired["responses"][-1]           # bg ran post-response
    assert url.endswith("/respond/xyz") and in_channel is True
    assert "Sources:" in text

    r = post_signed(c, "/hooks/slack/commands", cmd_body("/ask", ""))
    assert "Usage" in r.json()["text"] and len(wired["responses"]) == 1


def test_slash_ask_refusal_logs_routed_gap(seeded, wired):
    c = client(seeded)
    post_signed(c, "/hooks/slack/commands",
                cmd_body("/ask", "What is the espresso machine warranty for "
                                 "the lunar office?"))
    _, text, _ = wired["responses"][-1]
    assert "gap" in text.lower()
    assert any("espresso" in g["question"].lower() for g in list_gaps(seeded))


def test_slash_teach_captures_vouched_knowledge_with_provenance(seeded, wired):
    c = client(seeded)
    for line in ("Guardian never shows D4910 frequency history in the portal",
                 "confirmed again today — the voice line gives remaining count",
                 "so: always call the voice line for Guardian D4910 history"):
        post_signed(c, "/hooks/slack", ev(line))
    post_signed(c, "/hooks/slack/commands", cmd_body("/teach"))
    assert "Learned" in wired["responses"][-1][1]

    doc = seeded.execute(
        "SELECT * FROM documents WHERE id LIKE 'sl-teach-%'").fetchone()
    assert doc is not None
    assert doc["doc_type"] == "notes" and doc["source_type"] == "slack"
    prov = doc["provenance"]
    assert prov["captured_by"] == "marcus" and prov["via"] == "slack-teach"
    assert prov["chat"] == "#ops-war-room"

    hits = search(seeded, "Guardian D4910 frequency history voice line")
    assert any(r.doc_id.startswith("sl-teach-") for r in hits)
    left = seeded.execute("SELECT count(*) AS n FROM connector_messages "
                          "WHERE source = 'slack' AND processed = FALSE").fetchone()
    assert left["n"] == 0
    post_signed(c, "/hooks/slack/commands", cmd_body("/teach"))
    assert "Nothing new" in wired["responses"][-1][1]


def test_slash_team_routes_channel_knowledge(seeded, wired):
    c = client(seeded)
    r = post_signed(c, "/hooks/slack/commands", cmd_body("/team", "gtm"))
    assert r.json()["response_type"] == "in_channel"
    row = seeded.execute(
        "SELECT source, team, title FROM connector_chats WHERE chat_id = 'C42WAR'").fetchone()
    assert row["team"] == "gtm" and row["source"] == "slack"
    assert row["title"] == "ops-war-room"                    # name learned from the command
    r = post_signed(c, "/hooks/slack/commands", cmd_body("/team", "accounting"))
    assert "Unknown team" in r.json()["text"]


def test_ambient_digest_keeps_per_source_profiles(seeded, wired):
    """The shared digester must file each source under its own identity —
    slack runs as slack_thread/sl-*, telegram runs as chat_thread/tg-* —
    even when both have quiet chats pending in the same pass."""
    c = client(seeded)
    old_s = -7200.0
    for line in ("MetLife navigator logins failing again on the 1st",
                 "it's the MFA seed rotation, same as INC-2026-041",
                 "workaround: re-enroll MFA on the 1st before 9am ET"):
        post_signed(c, "/hooks/slack",
                    ev(line, channel="C9FIRE", msg_ts=ts(old_s)))
    # the tail-call on the third (already-quiet) arrival flushed the slack run
    sdoc = seeded.execute("SELECT * FROM documents WHERE id LIKE 'sl-digest-%'").fetchone()
    assert sdoc is not None
    assert sdoc["doc_type"] == "slack_thread" and sdoc["source_type"] == "slack"
    assert sdoc["provenance"]["via"] == "slack-digest"
    assert sdoc["source_url"].startswith("slack://C9FIRE/")

    old_t = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
    for i, line in enumerate(("payer portal quirk one", "quirk two", "quirk three")):
        tg.handle_update(seeded, {"update_id": 1, "message": {
            "message_id": 9000 + i, "date": old_t, "text": line,
            "chat": {"id": -200600, "type": "supergroup", "title": "eng-firefight"},
            "from": {"id": 7, "username": "marcus"}}})
    tdoc = seeded.execute("SELECT * FROM documents WHERE id LIKE 'tg-digest-%'").fetchone()
    assert tdoc is not None
    assert tdoc["doc_type"] == "chat_thread" and tdoc["source_type"] == "telegram"
    assert tdoc["provenance"]["via"] == "telegram-digest"
    assert tg.run_ambient_digest(seeded) == 0                # nothing left unprocessed
