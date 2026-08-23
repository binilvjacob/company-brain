---
title: Feature flag registry
team: product
doc_type: spec
owner: lena
updated_at: 2026-07-19
entities: [feature flags]
---
# Feature flag registry

Flags are per-customer unless marked global. Owner = who can flip it.

## Verification
- `priority-lane` (GA default on) — same-day appointment rush lane. Owner: ops.
- `voice-fallback` (GA default on) — voice agent when portal can't answer.
  Off only for customers who contractually forbid payer calls (1 today).
- `writeback-dry-run` (default on first 14 days) — write-back preview mode:
  results staged, practice approves postings. Owner: implementation.
- `deep-history-pull` (opt-in) — 24-month claims-history retrieval for
  frequency computation on high-value procedures. Adds ~40s per verification.
- `pregnancy-program-check` (global, on) — surfaces payer maternity program
  flags (Aetna EOB-MAT pattern).

## Claims beta
- `claims-beta` (8 practices) — module master switch. Owner: Lena only.
- `claims-auto-attach` (subset of 3) — auto-attachment of charting/x-rays from
  PMS document store.

## Experimental
- `agent-context-notes` (internal, 2 pilot customers) — feeds recent
  specialist resolution notes for the same payer into the agent's context at
  verification time. Early data: small STR lift on frequency-reason flags.
  This is the seed of the "agents read the Brain" direction.

## Retired
- `edi-first` — try EDI 271 before portal. Retired 2026-04: 271 data too
  shallow for frequency/history; portal-first with EDI cross-check won.
