"""/ask — cited answers with calibrated refusal.

Three hard rules:
1. Every claim carries an inline [n] citation resolving to a real chunk.
2. Staleness is surfaced, not hidden ("newest source is 8 months old").
3. Below the confidence gate — or if the model can't ground the answer — the
   Brain refuses and writes a knowledge_gaps row routed to a likely owner.

Rule 3 is the founder's own stated concern ("AI makes mistakes silently")
encoded as a system property. A Brain that confidently invents a frequency
limitation is worse than no Brain at this company.
"""
import re
import time
from datetime import datetime, timezone

import psycopg

from app import config
from app.llm import generate_json, generation_cost_usd
from app.retrieval import RetrievedChunk, confidence, search

SYSTEM_PROMPT = """You are Needletail's Company Brain, an internal knowledge tool.
Answer ONLY from the numbered context blocks. Rules:
- Every factual claim must end with an inline citation like [1] or [2][3]
  referring to the context block it came from. No uncited claims.
- If blocks disagree, prefer the most recently updated one, say that you did,
  and cite both.
- If the context does not contain the answer, set can_answer to false. Never
  guess. An honest refusal is a correct answer.
- Keep answers tight: 2-6 sentences, markdown, no preamble.
Return JSON: {"can_answer": bool, "answer_markdown": str, "citations": [int],
"staleness_note": str|null, "reason": str|null}"""


def _context_block(results: list[RetrievedChunk]) -> str:
    parts = []
    for i, r in enumerate(results, 1):
        loc = f"{r.title}" + (f" > {r.heading}" if r.heading else "")
        parts.append(
            f"[{i}] ({r.doc_type}, team={r.team}, updated {r.updated_at:%Y-%m-%d}, owner={r.owner})\n"
            f"{loc}\n{r.text}"
        )
    return "\n\n".join(parts)


def _staleness(cited: list[RetrievedChunk]) -> str | None:
    if not cited:
        return None
    newest = max(c.updated_at for c in cited)
    age = (datetime.now(timezone.utc) - newest).days
    if age > config.STALENESS_WARN_DAYS:
        return f"Newest cited source is {age} days old — may be stale."
    return None


def _normalize_question(q: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()[:300]


def log_gap(conn: psycopg.Connection, q: str, role: str,
            results: list[RetrievedChunk], source: str = "live") -> dict:
    team_guess = results[0].team if results else "ops"
    owner = config.TEAM_OWNER.get(team_guess, "priya")
    conn.execute(
        """
        INSERT INTO gaps (question, normalized, asked_by_role, routed_owner, team_guess, source)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (normalized) DO UPDATE SET
          count = gaps.count + 1, last_asked = now(), status = 'open'
        """,
        (q, _normalize_question(q), role, owner, team_guess, source),
    )
    return {"routed_owner": owner, "team_guess": team_guess}


def ask(conn: psycopg.Connection, q: str, role: str = "everyone",
        teams: list[str] | None = None) -> dict:
    t0 = time.perf_counter()
    cost0 = generation_cost_usd()
    results = search(conn, q, role=role, teams=teams)
    conf = confidence(results)

    if conf < config.CONFIDENCE_THRESHOLD:
        gap = log_gap(conn, q, role, results)
        out = {
            "answered": False, "confidence": round(conf, 3),
            "message": (f"I don't have this. Logged as a knowledge gap and routed "
                        f"to @{gap['routed_owner']} ({gap['team_guess']})."),
            **gap, "citations": [],
        }
    else:
        resp = generate_json(SYSTEM_PROMPT, f"Question: {q}\n\nContext:\n\n{_context_block(results)}")
        cited_idx = [i for i in resp.get("citations", [])
                     if isinstance(i, int) and 1 <= i <= len(results)]
        if not resp.get("can_answer") or not cited_idx:
            gap = log_gap(conn, q, role, results)
            out = {
                "answered": False, "confidence": round(conf, 3),
                "message": (f"I found related material but can't ground an answer in it "
                            f"({resp.get('reason') or 'insufficient context'}). Logged as a gap "
                            f"and routed to @{gap['routed_owner']}."),
                **gap, "citations": [],
            }
        else:
            cited = [results[i - 1] for i in cited_idx]
            out = {
                "answered": True, "confidence": round(conf, 3),
                "answer_markdown": resp["answer_markdown"],
                "staleness_note": resp.get("staleness_note") or _staleness(cited),
                "citations": [{
                    "n": i, "chunk_id": results[i - 1].chunk_id,
                    "doc_id": results[i - 1].doc_id, "title": results[i - 1].title,
                    "heading": results[i - 1].heading, "doc_type": results[i - 1].doc_type,
                    "team": results[i - 1].team, "owner": results[i - 1].owner,
                    "updated_at": f"{results[i - 1].updated_at:%Y-%m-%d}",
                    "source_url": results[i - 1].source_url,
                } for i in cited_idx],
            }

    latency_ms = int((time.perf_counter() - t0) * 1000)
    out["latency_ms"] = latency_ms
    out["cost_usd"] = round(generation_cost_usd() - cost0, 6)
    conn.execute(
        "INSERT INTO query_log (q, role, answered, latency_ms, cost_usd) VALUES (%s, %s, %s, %s, %s)",
        (q, role, out["answered"], latency_ms, out["cost_usd"]),
    )
    return out
