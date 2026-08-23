---
title: Per-payer request budget & rate-limit policy
team: eng
doc_type: policy
owner: dana
updated_at: 2026-07-13
entities: [rate limits, navigators]
---
# Per-payer request budget & rate-limit policy

## Principle
We are guests on payer infrastructure. Budgets are set to stay *well under*
observed limits, with jitter, and we never bypass bot defense (no CAPTCHA
solving, no header spoofing beyond a standard browser profile). The durable
fix is always negotiated access (API/EDI), pursued through provider relations.

## Current budgets (requests/hour/IP unless noted)
- UHC: 25 (observed limit ~30 since INC-2026-055)
- DDCA: 60 (no observed limit; self-imposed)
- MetLife: session-budget model instead — max 1 session per member, 8-min cap
- Cigna DPPO: 45 · Cigna DHMO: n/a (voice-dominant)
- Aetna: 50, with a freeze on bulk endpoints on the 1st (stale-cache day)
- Guardian: 40 (provisions only; history is voice)
- FEP: 30

## Mechanics
Budgets live in per-payer config (moved out of code after INC-2026-055) with
alarms when observed 429/CAPTCHA rates suggest the payer moved their limit.
Batching rule everywhere: one member = one session = every question we have.

## Review
Monthly, or on any bot-defense incident. Changes canary for 2 hours like nav
specs.
