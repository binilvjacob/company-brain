# Needletail Company Brain

> **Thesis: Needletail's Company Brain is not a chatbot over Notion. It is the memory layer of the human-in-the-loop.**
>
> Needletail's unit economics are governed by two numbers: what % of verifications need a human, and how long each human touch takes. Every human touch is, structurally, a knowledge lookup — and today that knowledge is generated fresh every day by the ops team and then thrown away. The Brain serves cited answers fast, refuses honestly when it doesn't know, and captures every resolved exception back into itself. Brain → faster human touches → captured resolutions → better Brain → fewer exceptions.

## Quickstart (60 seconds)

```bash
cp .env.example .env   # add OPENAI_API_KEY
docker compose up --build
# → http://localhost:8000  (UI)
# → http://localhost:8000/docs  (Brain API)
make seed              # ingest the corpus
make eval              # reproduce the eval table
```

## Architecture

_(diagram + eval table land here before submission)_

## Layout

- `corpus/` — 50–70 synthetic Needletail documents, by team. See `DATA.md`.
- `app/adapters/` — SourceAdapter interface: markdown, csv, slack_export (real), notion (typed stub).
- `app/` — ingest → chunk/embed → hybrid retrieval (BM25 + pgvector + RRF) → cited answers with calibrated refusal → recipes → capture loop.
- `eval/` — golden questions + `run_eval.py`.
