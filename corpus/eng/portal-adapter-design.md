---
title: Portal adapter (navigator) design & drift defense
team: eng
doc_type: spec
owner: dana
updated_at: 2026-05-16
entities: [navigators, nav specs, drift]
---
# Portal adapter (navigator) design & drift defense

## Nav specs
One YAML per payer portal: auth flow, page flows, selectors, extraction maps,
and **assertions** — expected page landmarks that must be present after each
step. Assertions are the drift tripwire: a missing landmark fails fast with a
screenshot instead of extracting garbage.

## Versioning & rollout
Nav specs deploy independently of code, canary on 5% of that payer's jobs for
2 hours, then full. Rollback is a version pin. Every extraction carries the
spec version in provenance — QA can trace any wrong answer to the exact spec
that produced it.

## Drift defense in layers
1. Assertions fail fast (above).
2. **Schema sanity checks** on extracted data: accumulators must be numeric,
   dates parseable, remaining ≤ total. Violations flag, never write back.
3. **Canary members**: synthetic test verifications per top payer run hourly;
   a canary failure pages before customer volume hurts.
4. Cross-source disagreement (portal vs EDI vs recent history) raises the
   flag rate automatically for that payer while eng investigates.

## Auth & session hygiene
Per-office credentials in the vault, MFA secrets rotated on payer schedule
(see INC-2026-041 for what happens when a payer rotates off-schedule).
Session budgets per payer (MetLife 8-min timeout drove this design).
IP strategy per payer: UHC rotates at 25 req/hr since INC-2026-055.

## When a portal is down
Conductor flips the payer to voice-first automatically after 3 consecutive
auth/landmark failures, and un-flips on canary recovery. Practices see a
status banner, not silence.
