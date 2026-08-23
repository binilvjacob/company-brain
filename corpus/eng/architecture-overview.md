---
title: System architecture overview
team: eng
doc_type: spec
owner: nakul
updated_at: 2026-03-08
entities: [architecture, Conductor, navigators, voice agents]
---
# System architecture overview

## The shape
Event-driven pipeline around a central orchestrator ("Conductor"):

PMS schedule sync → verification jobs → Conductor → [navigators | voice
agents | EDI cross-check] → resolver → confidence gate → {write-back |
exception queue} → PMS write-back workers.

## Conductor
Owns job state, retries, and source selection per payer (portal-first, voice
fallback, EDI cross-check where a payer's 271 is worth reading). Every
decision it makes is written to the job's provenance log — the queue UI and QA
both read from that log, never from agent memory.

## Navigators
Browser-automation workers driven by **per-payer YAML nav specs** (selectors,
flows, data extraction maps). Nav specs are versioned; a failing spec rolls
back independently. ~400 portals; top-7 payers get dedicated worker pools and
tighter drift alarms.

## Voice agents
Telephony + realtime speech pipeline; **DTMF-first** IVR traversal from
per-payer IVR maps, speech only where menus require it. Calls are recorded,
transcribed, and the answer extraction is confidence-gated the same as portal
data — a mumbled accumulator does not silently become a number.

## Resolver & confidence gate
Merges sources with per-field precedence rules (accumulators: voice > portal >
EDI; provisions: portal > voice). Procedure-level frequency math happens here.
Below-threshold confidence or source disagreement ⇒ flag with reason code —
**the system never guesses; that is a product invariant, not a tuning
choice.**

## Write-back
Per-PMS workers (Dentrix, Open Dental, Eaglesoft, Curve Hero) with idempotency
keys, dry-run mode, and an audit log per posted field. Curve Hero is API
rate-limited; batches post in 5-minute windows.

## Data boundaries
Verification results and provenance live in our Postgres. Raw member
identifiers stay in transient job scope and the customer's PMS; long-term
stores hold `member_ref` links only.
