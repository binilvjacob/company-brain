"""Hybrid retrieval: lexical + vector, fused with RRF, then metadata boosts.

Why hybrid, specifically: Needletail's vocabulary is proper nouns and codes —
"Delta Dental of California", "D4910", "Eaglesoft". Pure semantic search is
genuinely weak at exact-token matching on these (it will happily return the
MetLife playbook for a Cigna question). The lexical arm is load-bearing here,
not a nice-to-have.

Score = [RRF(lexical) + RRF(vector)]
        × (1 + W_FRESHNESS·exp(-age/half_life)   (a 3-week-old correction should
           + W_AUTHORITY·doc_type_weight          outrank an 8-month-old SOP, and
           + W_TEAM_MATCH·team_match)             an SOP should outrank a Slack
                                                  message at EQUAL relevance)
Boosts are multiplicative because RRF's dynamic range is tiny — additive
boosts at any useful magnitude drown relevance and float fresh-but-irrelevant
documents to the top (caught by the eval harness, kept as a failure note).
Visibility is a hard filter, not a boost: a doc tagged leadership-only never
enters the candidate set for other roles.

The lexical arm runs websearch semantics (AND) first for precision, then falls
back to an OR-of-terms query when AND is too strict — natural-language
questions rarely contain every word of the answer's chunk.
"""
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg

from app import config
from app.embeddings import embed_one


@dataclass
class RetrievedChunk:
    chunk_id: int
    doc_id: str
    title: str
    heading: str
    text: str
    team: str
    doc_type: str
    owner: str
    source_url: str
    updated_at: datetime
    score: float
    cosine_sim: float
    lexical_rank: int | None
    vector_rank: int | None


def _visibility_for(role: str) -> list[str]:
    if role == "leadership":
        return ["everyone", "ops", "leadership"]
    if role == "ops":
        return ["everyone", "ops"]
    return ["everyone"]


def expand_query(q: str) -> str:
    """One cheap rewrite pass: expand the acronyms this domain lives on."""
    extras = [full for abbr, full in config.ACRONYMS.items()
              if f" {abbr.lower()} " in f" {q.lower()} " or f" {abbr.lower()}?" in f" {q.lower()}?"]
    return q + (" (" + "; ".join(extras) + ")" if extras else "")


def search(conn: psycopg.Connection, q: str, role: str = "everyone",
           teams: list[str] | None = None, top_k: int | None = None,
           doc_types: list[str] | None = None) -> list[RetrievedChunk]:
    top_k = top_k or config.TOP_K
    # Acronym expansion feeds the VECTOR arm only: websearch_to_tsquery ANDs its
    # terms, so padding the lexical query with expansions would turn a match into
    # a miss. Exact tokens for lexical, enriched meaning for vector.
    expanded = expand_query(q)
    vis = _visibility_for(role)
    n = config.CANDIDATES_PER_ARM

    filters = "d.visibility && %s"
    params: list = [vis]
    if teams:
        filters += " AND d.team = ANY(%s)"
        params.append(teams)
    if doc_types:
        filters += " AND d.doc_type = ANY(%s)"
        params.append(doc_types)

    lex_rows = conn.execute(
        f"""
        SELECT c.id, ts_rank_cd(c.tsv, websearch_to_tsquery('english', %s)) AS r
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE c.tsv @@ websearch_to_tsquery('english', %s) AND {filters}
        ORDER BY r DESC LIMIT {n}
        """,
        [q, q, *params],
    ).fetchall()
    if len(lex_rows) < 5:
        # AND semantics too strict for this phrasing — retry as OR-of-terms.
        terms = " | ".join(re.findall(r"[a-zA-Z0-9]+", q))
        if terms:
            lex_rows = conn.execute(
                f"""
                SELECT c.id, ts_rank_cd(c.tsv, to_tsquery('english', %s)) AS r
                FROM chunks c JOIN documents d ON d.id = c.doc_id
                WHERE c.tsv @@ to_tsquery('english', %s) AND {filters}
                ORDER BY r DESC LIMIT {n}
                """,
                [terms, terms, *params],
            ).fetchall()

    qvec = str(embed_one(expanded))
    vec_rows = conn.execute(
        f"""
        SELECT c.id, 1 - (c.embedding <=> %s::vector) AS sim
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE {filters}
        ORDER BY c.embedding <=> %s::vector LIMIT {n}
        """,
        [qvec, *params, qvec],
    ).fetchall()

    lex_rank = {row["id"]: i + 1 for i, row in enumerate(lex_rows)}
    vec_rank = {row["id"]: i + 1 for i, row in enumerate(vec_rows)}
    cosine = {row["id"]: float(row["sim"]) for row in vec_rows}
    candidates = set(lex_rank) | set(vec_rank)
    if not candidates:
        return []

    meta = {row["id"]: row for row in conn.execute(
        """
        SELECT c.id, c.doc_id, c.heading, c.text, d.title, d.team, d.doc_type,
               d.owner, d.source_url, d.updated_at
        FROM chunks c JOIN documents d ON d.id = c.doc_id WHERE c.id = ANY(%s)
        """,
        [list(candidates)],
    ).fetchall()}

    now = datetime.now(timezone.utc)
    scored: list[RetrievedChunk] = []
    for cid in candidates:
        m = meta[cid]
        rrf = sum(1.0 / (config.RRF_K + r[cid])
                  for r in (lex_rank, vec_rank) if cid in r)
        age_days = max((now - m["updated_at"]).days, 0)
        freshness = math.exp(-age_days / config.FRESHNESS_HALF_LIFE_DAYS)
        authority = config.DOC_TYPE_AUTHORITY.get(m["doc_type"], 0.7)
        team_match = 1.0 if teams and m["team"] in teams else 0.0
        multiplier = (1.0
                      + config.W_FRESHNESS * freshness
                      + config.W_AUTHORITY * authority
                      + config.W_TEAM_MATCH * team_match)
        scored.append(RetrievedChunk(
            chunk_id=cid, doc_id=m["doc_id"], title=m["title"],
            heading=m["heading"] or "", text=m["text"], team=m["team"],
            doc_type=m["doc_type"], owner=m["owner"], source_url=m["source_url"],
            updated_at=m["updated_at"],
            score=rrf * multiplier,
            cosine_sim=cosine.get(cid, 0.0),
            lexical_rank=lex_rank.get(cid),
            vector_rank=vec_rank.get(cid),
        ))

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]


def confidence(results: list[RetrievedChunk]) -> float:
    """Absolute confidence in [0,1] for the refusal gate.

    Uses the best cosine similarity across the result set — not the score of the
    boost-adjusted top item — because boosts (freshness, authority) can float a
    fresh-but-irrelevant chunk to rank 1 when nothing is actually relevant, and
    the gate must measure relevance, not recency. Bonus when the lexical and
    vector arms agree on that best hit.
    """
    if not results:
        return 0.0
    best = max(results, key=lambda r: r.cosine_sim)
    agree = 0.15 if (best.lexical_rank and best.lexical_rank <= 5
                     and best.vector_rank and best.vector_rank <= 5) else 0.0
    return min(max(best.cosine_sim, 0.0) + agree, 1.0)
