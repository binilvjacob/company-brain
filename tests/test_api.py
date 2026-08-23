"""API surface smoke tests (mock providers, real Postgres)."""
from fastapi.testclient import TestClient

from app.api import app


def client(seeded):
    app.state.conn = seeded
    return TestClient(app)


def test_healthz_and_ask_roundtrip(seeded):
    c = client(seeded)
    health = c.get("/healthz").json()
    assert health["ok"] and health["docs"] >= 4

    r = c.post("/ask", json={"q": "Delta Dental of California D4910 frequency rule"}).json()
    assert r["answered"] is True and r["citations"]

    r = c.post("/search", json={"q": "voice agent DTMF IVR"}).json()
    assert r["results"] and r["results"][0]["doc_id"] == "voice-runbook"


def test_ingest_endpoint_and_gaps(seeded):
    c = client(seeded)
    r = c.post("/ingest", json={
        "id": "api-doc-1", "title": "API-added note", "body": "Pinnacle uses Dentrix.",
        "team": "ops", "doc_type": "notes", "owner": "priya",
    }).json()
    assert r["chunks"] >= 1

    c.post("/ask", json={"q": "completely unrelated quantum blockchain question"})
    gaps = c.get("/gaps").json()["gaps"]
    assert any("quantum" in g["question"] for g in gaps)


def test_recipe_create_and_run_over_api(seeded):
    c = client(seeded)
    made = c.post("/recipes", json={
        "name": "Eng oncall brief",
        "inputs": [{"name": "system", "type": "text"}],
        "retrieval": {"query": "{system} runbook incident", "top_k": 5},
        "prompt": "Brief the oncall about {system}. Cite everything.",
    }).json()
    assert made["slug"] == "eng-oncall-brief"
    run = c.post(f"/recipes/{made['slug']}/run",
                 json={"inputs": {"system": "voice agent IVR"}}).json()
    assert run["answered"] is True
