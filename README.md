# Needletail Company Brain

> **The Company Brain is not a chatbot over Notion. It is the memory layer of
> Needletail's human-in-the-loop.** Every exception a specialist resolves is a
> knowledge lookup someone will repeat tomorrow — today that knowledge is
> generated hourly and thrown away. The Brain serves cited answers, refuses
> honestly when it doesn't know, routes every gap to an owner, and captures
> every resolution back into itself. Brain → faster human touches → captured
> resolutions → richer Brain → fewer exceptions. That's how 85%
> straight-through becomes 92% without retraining a model.

**Live demo:** {LIVE_URL} · **Writeup:** [WRITEUP.md](WRITEUP.md) ·
**Data statement:** [DATA.md](DATA.md) (everything is synthetic)

## 60-second quickstart

```bash
cp .env.example .env       # put your OPENAI_API_KEY in it
docker compose up --build  # → http://localhost:8000 (seeds itself on first boot)
```

No key? It still runs: retrieval is fully live, generation degrades to a
deterministic mock. `make eval` reproduces the eval table; `make test` runs
the suite against real Postgres.

## What it does

- **Ask** — plain-English questions → answers where *every claim* carries a
  clickable citation, staleness is surfaced ("newest source is 8 months old"),
  and conflicting sources resolve toward the freshest with the conflict shown.
- **Refuse** — below the confidence gate, or when the model can't ground an
  answer: *"I don't have this — logged as a gap, routed to @owner."* Silent
  wrong answers are the failure mode this company exists to prevent; the Brain
  encodes that as a system property.
- **Recipes** — saved, shareable mini-tools (inputs + retrieval template +
  prompt) anyone can build in a five-field form. Ships with **Exception Triage
  Assist** (governing rule + the most similar past resolutions + a suggested
  decision), Payer Playbook Lookup, and a GTM Objection Responder. Every
  recipe is also an API endpoint: `POST /recipes/{slug}/run`.
- **Capture** — "Teach the Brain": one click turns a resolved exception into
  retrievable, cited memory with full provenance. The Gaps dashboard is what
  the company most needs to write down, ranked by how often someone asked.

## Architecture

```
corpus/ ─→ SourceAdapters (markdown · csv · slack export · notion stub)
              └─→ KnowledgeObject ─→ redact PHI ─→ chunk (title>heading prefix) ─→ embed
                                        │
                    ┌───────────────────▼────────────────────┐
                    │   Postgres 16 · pgvector · tsvector    │   one database
                    └───────────────────┬────────────────────┘
        lexical (websearch → OR fallback) ─┐
                                           ├─ RRF × (1 + freshness + authority + team)
        vector (cosine) ───────────────────┘        │
                                     visibility hard-filter
                                                    │
     /ask ── cited answer ─ staleness ─ confidence gate ─ refuse → gaps (routed)
     /recipes/{slug}/run ── Recipes ── Recipe Builder (no-code)
     "Teach the Brain" ──→ /ingest (provenance) ──→ back into the index
```

Design choices that matter (argued fully in the [writeup](WRITEUP.md)):
lexical search is load-bearing in a vocabulary of CDT codes and payer names;
metadata boosts are *multiplicative tie-breakers* so freshness can settle a
near-tie but never outvote relevance; visibility is a hard filter, not a
ranking signal; refusal is calibrated from a measured threshold sweep, not
picked by feel.

## Eval

31 golden questions (25 answerable across ops/product/eng/GTM/G&A, 6 that
must be refused — including a visibility trap). Written before tuning;
reproduce with `make eval`.

| Metric | Value |
|---|---|
| Recall@5 | {RECALL} |
| Answer rate (answerable) | {ANSWER_RATE} |
| Groundedness (LLM-judged) | {GROUND} |
| Refusal accuracy | {REFUSAL} |
| p50 latency | {P50} ms |
| Mean cost/query | ${COST} |

Failure modes are listed honestly in [WRITEUP.md §6](WRITEUP.md) — including
the ranking bug the eval caught before it shipped.

## Layout

```
corpus/          114 synthetic knowledge objects, by team (see DATA.md)
  recipes/       the three shipped recipe definitions (YAML)
app/
  adapters/      SourceAdapter interface: markdown, csv, slack_export, notion stub
  redact.py      PHI stripping at ingest
  chunking.py    heading-aware chunks with contextual prefixes
  retrieval.py   hybrid lexical+vector, RRF, boosts, visibility
  answer.py      citation contract, confidence gate, refusal → gaps
  recipes.py     declarative recipe engine + builder
  capture.py     Teach the Brain + gaps
  api.py         Brain API + HTMX UI (Ask · Recipes · Gaps · Sources)
eval/            golden set + harness
tests/           12 tests over real Postgres (mock LLM/embeddings)
.github/         CI: test → eval (real providers) → deploy → self-reported results
```

## What I deliberately didn't build

Live OAuth connectors (the adapter interface + typed Notion stub is the seam —
a real connector is a ~50-line file), auth/SSO (doc-level visibility tags +
role switcher demonstrate the model), LangChain/LlamaIndex (I want to be able
to explain every retrieval decision), a separate vector DB (Postgres already
does rows + full-text + vectors), and fine-tuning (nothing here needs it).
Reasoning for each: [WRITEUP.md §2](WRITEUP.md).
