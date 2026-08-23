"""Recipes: the composition layer — "any team member builds a small tool".

A Recipe is a saved, named, shareable mini-tool: typed inputs + a retrieval
query template + a prompt + an output format. Declarative rather than
hardcoded, because a recipe FORMAT generalizes to the hundredth tool nobody
will ever write by hand. Runnable in the UI at /r/{slug} and over the API at
POST /recipes/{slug}/run — that second surface is what makes the Brain a
platform instead of an app.

`include_similar` is the option behind the headline Exception Triage Assist
recipe: a second retrieval pass restricted to past resolutions, so the tool
returns "here's how we decided this before", not just documents.
"""
import json
import re
import time

import psycopg
import yaml

from app.answer import SYSTEM_PROMPT, _context_block, log_gap
from app.llm import generate_json
from app.retrieval import confidence, search


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def _fill(template: str, inputs: dict) -> str:
    return template.format_map(_SafeDict(**inputs))


def list_recipes(conn: psycopg.Connection) -> list[dict]:
    return conn.execute("SELECT * FROM recipes ORDER BY created_at").fetchall()


def get_recipe(conn: psycopg.Connection, slug: str) -> dict | None:
    return conn.execute("SELECT * FROM recipes WHERE slug = %s", (slug,)).fetchone()


def save_recipe(conn: psycopg.Connection, spec: dict, created_by: str = "system") -> str:
    slug = spec.get("slug") or re.sub(r"[^a-z0-9]+", "-", spec["name"].lower()).strip("-")
    conn.execute(
        """
        INSERT INTO recipes (slug, name, description, inputs, retrieval, prompt, output, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (slug) DO UPDATE SET
          name = EXCLUDED.name, description = EXCLUDED.description,
          inputs = EXCLUDED.inputs, retrieval = EXCLUDED.retrieval,
          prompt = EXCLUDED.prompt, output = EXCLUDED.output
        """,
        (slug, spec["name"], spec.get("description", ""),
         json.dumps(spec.get("inputs", [])), json.dumps(spec["retrieval"]),
         spec["prompt"], spec.get("output", "card"), created_by),
    )
    return slug


def seed_recipes_from_dir(conn: psycopg.Connection, recipes_dir) -> int:
    n = 0
    for path in sorted(recipes_dir.glob("*.yaml")):
        save_recipe(conn, yaml.safe_load(path.read_text(encoding="utf-8")))
        n += 1
    return n


def run_recipe(conn: psycopg.Connection, slug: str, inputs: dict,
               role: str = "everyone") -> dict:
    recipe = get_recipe(conn, slug)
    if not recipe:
        return {"error": f"no recipe '{slug}'"}
    t0 = time.perf_counter()
    retrieval = recipe["retrieval"]

    query = _fill(retrieval["query"], inputs)
    results = search(
        conn, query, role=role,
        teams=(retrieval.get("filters") or {}).get("team"),
        doc_types=(retrieval.get("filters") or {}).get("doc_type"),
        top_k=retrieval.get("top_k", 12),
    )

    similar_block = ""
    sim_cfg = retrieval.get("include_similar")
    if sim_cfg:
        sim = search(conn, query, role=role,
                     doc_types=[sim_cfg.get("doc_type", "resolution")],
                     top_k=sim_cfg.get("top_k", 3))
        seen = {r.chunk_id for r in results}
        sim = [s for s in sim if s.chunk_id not in seen]
        results = results + sim
        if sim:
            similar_block = (
                "\n\nThe blocks numbered "
                f"[{results.index(sim[0]) + 1}]..[{len(results)}] are the most similar PAST "
                "RESOLUTIONS from the exception queue — surface what the specialist decided and why."
            )

    conf = confidence(results)
    if not results:
        gap = log_gap(conn, query, role, results)
        return {"answered": False, "confidence": conf,
                "message": f"Nothing relevant in the Brain — logged as a gap, routed to @{gap['routed_owner']}.",
                "citations": [], "latency_ms": int((time.perf_counter() - t0) * 1000)}

    prompt = _fill(recipe["prompt"], inputs)
    resp = generate_json(
        SYSTEM_PROMPT,
        f"Task:\n{prompt}{similar_block}\n\nContext:\n\n{_context_block(results)}",
    )
    cited_idx = [i for i in resp.get("citations", [])
                 if isinstance(i, int) and 1 <= i <= len(results)]
    return {
        "answered": bool(resp.get("can_answer")) and bool(cited_idx),
        "confidence": round(conf, 3),
        "answer_markdown": resp.get("answer_markdown", ""),
        "reason": resp.get("reason"),
        "citations": [{
            "n": i, "chunk_id": results[i - 1].chunk_id, "doc_id": results[i - 1].doc_id,
            "title": results[i - 1].title, "heading": results[i - 1].heading,
            "doc_type": results[i - 1].doc_type, "team": results[i - 1].team,
            "owner": results[i - 1].owner,
            "updated_at": f"{results[i - 1].updated_at:%Y-%m-%d}",
            "source_url": results[i - 1].source_url,
        } for i in cited_idx],
        "latency_ms": int((time.perf_counter() - t0) * 1000),
    }
