"""Telegram connector tests: webhook auth, boundary redaction, /ask replies,
/teach capture with provenance, /team routing, ambient digestion of quiet
chats. Mock providers, real Postgres — same posture as the rest of the suite."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import app
from app.capture import list_gaps
from app.connectors import telegram as tg
from app.retrieval import search

_MSG_ID = iter(range(1000, 9999))


def upd(text, chat_id=-100500, user="marcus", title="ops-war-room", date=None):
    return {"update_id": 1, "message": {
        "message_id": next(_MSG_ID),
        "date": date or int(time.time()),
        "text": text,
        "chat": {"id": chat_id, "type": "supergroup", "title": title},
        "from": {"id": 7, "username": user, "first_name": "Marcus"},
    }}


@pytest.fixture
def sent(monkeypatch):
    """Capture outbound bot replies; enable the connector for the test."""
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(config, "CONNECTOR_SECRET", "shh-secret")
    out = []
    monkeypatch.setattr(tg, "send_message",
                        lambda chat_id, text, reply_to=None: out.append((str(chat_id), text)))
    return out


def client(seeded):
    app.state.conn = seeded
    return TestClient(app)


def test_webhook_auth_and_disabled_states(seeded, sent, monkeypatch):
    c = client(seeded)
    body = upd("hello")
    assert c.post("/hooks/telegram", json=body).status_code == 403  # no header
    ok = c.post("/hooks/telegram", json=body,
                headers={"x-telegram-bot-api-secret-token": "shh-secret"})
    assert ok.status_code == 200 and ok.json()["ok"] is True
    bad = c.post("/hooks/telegram", json=body,
                 headers={"x-telegram-bot-api-secret-token": "wrong"})
    assert bad.status_code == 403

    assert c.get("/healthz").json()["connectors"]["telegram"] is True
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    assert c.post("/hooks/telegram", json=body).status_code == 503
    assert c.get("/healthz").json()["connectors"]["telegram"] is False


def test_plain_message_buffered_with_boundary_redaction(seeded, sent):
    m = upd("DDCA note — Member ID: ABC1234567 and DOB: 04/12/1985, rule is 2 per year")
    tg.handle_update(seeded, m)
    tg.handle_update(seeded, m)  # Telegram retries must not duplicate
    rows = seeded.execute("SELECT * FROM connector_messages").fetchall()
    assert len(rows) == 1
    assert "ABC1234567" not in rows[0]["text"] and "04/12/1985" not in rows[0]["text"]
    assert "2 per year" in rows[0]["text"]
    assert rows[0]["processed"] is False
    assert sent == []  # buffering is silent


def test_ask_command_replies_with_citations(seeded, sent):
    tg.handle_update(seeded, upd("/ask What is the D4910 frequency rule for Delta Dental of California?"))
    assert len(sent) == 1
    chat_id, text = sent[0]
    assert "Sources:" in text and "Delta Dental of California" in text

    tg.handle_update(seeded, upd("/ask"))
    assert "Usage" in sent[-1][1]


def test_ask_refusal_logs_gap_in_chat(seeded, sent):
    tg.handle_update(seeded, upd("/ask What is the espresso machine warranty for the lunar office?"))
    assert "gap" in sent[-1][1].lower()
    assert any("espresso" in g["question"].lower() for g in list_gaps(seeded))


def test_teach_captures_vouched_knowledge_with_provenance(seeded, sent):
    for line in ("Guardian never shows D4910 frequency history in the portal",
                 "confirmed again today — the voice line gives remaining count",
                 "so: always call the voice line for Guardian D4910 history"):
        tg.handle_update(seeded, upd(line))
    tg.handle_update(seeded, upd("/teach"))
    assert "Learned" in sent[-1][1]

    doc = seeded.execute(
        "SELECT * FROM documents WHERE id LIKE 'tg-teach-%'").fetchone()
    assert doc is not None and doc["doc_type"] == "notes" and doc["source_type"] == "telegram"
    prov = doc["provenance"]
    assert prov["captured_by"] == "marcus" and prov["via"] == "telegram-teach"

    hits = search(seeded, "Guardian D4910 frequency history voice line")
    assert any(r.doc_id.startswith("tg-teach-") for r in hits)
    left = seeded.execute(
        "SELECT count(*) AS n FROM connector_messages WHERE processed = FALSE").fetchone()
    assert left["n"] == 0
    tg.handle_update(seeded, upd("/teach"))
    assert "Nothing new" in sent[-1][1]


def test_team_command_routes_chat_knowledge(seeded, sent):
    tg.handle_update(seeded, upd("hello there"))
    tg.handle_update(seeded, upd("/team gtm"))
    row = seeded.execute("SELECT team FROM connector_chats WHERE chat_id = '-100500'").fetchone()
    assert row["team"] == "gtm"
    tg.handle_update(seeded, upd("/team accounting"))
    assert "Unknown team" in sent[-1][1]


def test_ambient_digest_flushes_quiet_chats(seeded, sent):
    old = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
    for line in ("MetLife navigator logins failing again on the 1st",
                 "it's the MFA seed rotation, same as INC-2026-041",
                 "workaround: re-enroll MFA on the 1st before 9am ET"):
        tg.handle_update(seeded, upd(line, chat_id=-200600, title="eng-firefight", date=old))

    # the tail-call on the third (quiet-chat) arrival already flushed the run
    doc = seeded.execute("SELECT * FROM documents WHERE id LIKE 'tg-digest-%'").fetchone()
    assert doc is not None and doc["doc_type"] == "chat_thread"
    assert doc["provenance"]["via"] == "telegram-digest"
    assert tg.run_ambient_digest(seeded) == 0  # nothing left unprocessed

    # a fresh (not-quiet) chat must NOT digest
    tg.handle_update(seeded, upd("still chatting", chat_id=-300700, title="fresh-chat"))
    tg.handle_update(seeded, upd("very actively", chat_id=-300700, title="fresh-chat"))
    tg.handle_update(seeded, upd("right now", chat_id=-300700, title="fresh-chat"))
    assert tg.run_ambient_digest(seeded) == 0


def test_sync_endpoint_requires_token(seeded, sent):
    c = client(seeded)
    assert c.post("/sync/run").status_code == 403
    ok = c.post("/sync/run", headers={"x-sync-token": "shh-secret"})
    assert ok.status_code == 200 and "digests" in ok.json()
