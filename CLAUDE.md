# Build constraints (locked — do not re-litigate)

- Python + FastAPI. Postgres 16 + pgvector: one DB for rows, tsvector full-text, and vectors.
- Embeddings: OpenAI text-embedding-3-small. Generation behind a thin `app/llm.py` wrapper.
- UI: HTMX + Tailwind served by FastAPI. One process, no build step. Density over polish.
- NO LangChain/LlamaIndex, NO hosted RAG SaaS, NO agent frameworks, NO fine-tuning, NO auth system (doc-level `visibility` tags + a role dropdown instead), NO real OAuth connectors (adapter interface + mock data + typed Notion stub). Post-v1 amendment: token-based live connectors are in scope — the Telegram connector (webhook, no OAuth) shipped; OAuth ones (Slack/Drive/Gmail) remain out.
- Every claim in /ask carries a citation or the answer is a refusal + `knowledge_gaps` row.
- All corpus data is synthetic. Redaction pass at ingest. No PHI anywhere, ever.
- Eval before tuning; report Recall@5, groundedness, refusal accuracy, p50 latency, cost/query — including failures.
