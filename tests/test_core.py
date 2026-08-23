"""Unit + integration tests for the substrate: redaction, chunking, adapters,
hybrid retrieval, visibility, refusal, capture, recipes."""
import json
import textwrap
from pathlib import Path

from app.answer import ask
from app.capture import list_gaps, teach
from app.chunking import chunk_document
from app.recipes import run_recipe, save_recipe
from app.redact import redact
from app.retrieval import search


def test_redaction_strips_phi_shapes():
    text = textwrap.dedent("""\
        Patient: Jane Doe
        DOB: 04/12/1985
        Member ID: ABC1234567
        Callback: (555) 123-4567 and SSN 123-45-6789
        The frequency limitation is 2 per calendar year.""")
    clean, n = redact(text)
    assert "Jane Doe" not in clean
    assert "04/12/1985" not in clean
    assert "ABC1234567" not in clean
    assert "123-45-6789" not in clean
    assert "123-4567" not in clean
    assert "frequency limitation is 2 per calendar year" in clean
    assert n >= 5


def test_chunks_carry_title_and_heading_prefix():
    body = "## Frequency limitations\n" + ("D4910 rules apply. " * 300)
    chunks = chunk_document("DDCA Playbook", body)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.embed_text.startswith("DDCA Playbook > Frequency limitations")


def test_adapters_emit_canonical_objects(tmp_path: Path):
    (tmp_path / "ops").mkdir()
    (tmp_path / "meta").mkdir()
    (tmp_path / "ops" / "doc.md").write_text(textwrap.dedent("""\
        ---
        title: Test SOP
        team: ops
        doc_type: sop
        owner: priya
        updated_at: 2026-06-01
        entities: [Cigna]
        ---
        # Rule
        Body text.
        """))
    (tmp_path / "ops" / "resolutions.csv").write_text(
        "case_id,payer,procedure,flag_reason,portal_output,decision,reasoning,outcome,specialist,resolved_at\n"
        'EX-1,Aetna,D4341,missing perio chart,"benefits active",approved,"chart was attached in PMS",clean,anika,2026-07-01\n'
    )
    (tmp_path / "meta" / "slack-export.json").write_text(json.dumps({
        "channels": [{"name": "ops-payer-questions", "team": "ops", "threads": [{
            "thread_id": "t1", "topic": "DDCA correction",
            "messages": [{"user": "marcus", "ts": "1754300000", "text": "Portal disagrees with SOP"}],
        }]}]
    }))
    from app.adapters import load_corpus
    objs = {o.id: o for o in load_corpus(tmp_path)}
    assert objs["doc"].doc_type == "sop" and objs["doc"].team == "ops"
    assert objs["resolution-ex-1"].doc_type == "resolution"
    assert objs["slack-ops-payer-questions-t1"].doc_type == "slack_thread"
    assert all(o.updated_at.tzinfo for o in objs.values())


def test_hybrid_retrieval_prefers_fresh_source_in_contradiction(seeded):
    results = search(seeded, "Delta Dental of California D4910 perio maintenance frequency limitations")
    assert results, "retrieval returned nothing"
    doc_order = []
    for r in results:
        if r.doc_id not in doc_order:
            doc_order.append(r.doc_id)
    assert "ddca-playbook" in doc_order and "exception-sop" in doc_order
    assert doc_order.index("ddca-playbook") < doc_order.index("exception-sop"), \
        "freshness boost should rank the updated playbook above the stale SOP"


def test_visibility_is_a_hard_filter(seeded):
    q = "RCM Specialist L1 compensation band"
    everyone = search(seeded, q, role="everyone")
    leadership = search(seeded, q, role="leadership")
    assert all(r.doc_id != "comp-bands" for r in everyone)
    assert any(r.doc_id == "comp-bands" for r in leadership)

    # For "everyone", the restricted doc must never be cited — whether the ask
    # refuses outright or answers from other material. (With the real LLM the
    # grounding contract also forces refusal; the mock answers from whatever
    # context exists, so the leak check is the invariant to test here.)
    everyone_ask = ask(seeded, q, role="everyone")
    assert all(c["doc_id"] != "comp-bands" for c in everyone_ask.get("citations", []))
    answered = ask(seeded, q, role="leadership")
    assert answered["answered"] is True
    assert any(c["doc_id"] == "comp-bands" for c in answered["citations"])


def test_ask_cites_or_refuses_and_logs_gaps(seeded):
    good = ask(seeded, "What is the D4910 frequency rule for Delta Dental of California?")
    assert good["answered"] is True
    assert good["citations"], "every answer must carry citations"

    # A query with no overlap at all must fall below the confidence gate,
    # refuse, and log a gap. (Topic-adjacent unanswerables — e.g. a payer we
    # have no playbook for — are the real LLM's job to refuse via grounding;
    # that path is measured by the eval harness, not unit-testable with the
    # mock generator.)
    nonsense = "What is the espresso machine warranty policy for the lunar office?"
    bad = ask(seeded, nonsense)
    assert bad["answered"] is False
    gaps = list_gaps(seeded)
    assert any("espresso" in g["question"].lower() for g in gaps)

    ask(seeded, nonsense)
    gaps = list_gaps(seeded)
    row = [g for g in gaps if "espresso" in g["question"].lower()][0]
    assert row["count"] == 2, "repeat refusals should increment, not duplicate"


def test_capture_loop_makes_knowledge_retrievable(seeded):
    before = search(seeded, "Guardian D4910 frequency history voice call confirmation")
    assert all("guardian" not in r.title.lower() for r in before)

    teach(seeded, payer="Guardian", procedure="D4910",
          flag_reason="no portal frequency history",
          decision="verified via voice call — 2 remaining this year",
          reasoning="Guardian portal never exposes frequency history; the voice line "
                    "confirms remaining count. Always call for D4910.",
          author="marcus", case_ref="EX-2201")

    after = search(seeded, "Guardian D4910 frequency history voice call confirmation")
    assert any(r.doc_id.startswith("capture-") for r in after)
    doc = seeded.execute(
        "SELECT provenance FROM documents WHERE id LIKE 'capture-%' LIMIT 1").fetchone()
    prov = doc["provenance"]
    assert prov["captured_by"] == "marcus" and prov["case_ref"] == "EX-2201"


def test_recipes_engine_and_builder(seeded):
    slug = save_recipe(seeded, {
        "name": "Payer Playbook Lookup",
        "inputs": [{"name": "payer", "type": "text"}],
        "retrieval": {"query": "{payer} frequency limitations eligibility rules", "top_k": 6},
        "prompt": "Build a playbook card for {payer}. Cite every line.",
    }, created_by="chris")
    assert slug == "payer-playbook-lookup"

    result = run_recipe(seeded, slug, {"payer": "Delta Dental of California"})
    assert result["answered"] is True and result["citations"]


def test_triage_recipe_surfaces_similar_resolutions(seeded):
    save_recipe(seeded, {
        "slug": "triage-assist", "name": "Exception Triage Assist",
        "inputs": [{"name": "payer"}, {"name": "procedure"}, {"name": "flag_reason"}],
        "retrieval": {
            "query": "{payer} {procedure} {flag_reason} rule frequency",
            "top_k": 6,
            "include_similar": {"doc_type": "resolution", "top_k": 3},
        },
        "prompt": "Triage this flagged verification: {payer} {procedure} {flag_reason}.",
    })
    result = run_recipe(seeded, "triage-assist", {
        "payer": "Cigna", "procedure": "D4910", "flag_reason": "frequency history conflict"})
    cited_types = {c["doc_type"] for c in result["citations"]}
    retrieved = seeded  # readability
    assert result["answered"] is True
    # The similar-resolutions pass must actually inject past resolutions.
    assert any(c["doc_id"].startswith("resolution-") for c in result["citations"]) or \
           "resolution" in cited_types
