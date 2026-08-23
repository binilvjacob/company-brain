---
title: INC-2026-055 — UHC CAPTCHA rate-limit spike
team: eng
doc_type: runbook
owner: dana
updated_at: 2026-07-14
entities: [UnitedHealthcare, CAPTCHA, INC-2026-055]
---
# INC-2026-055 — UHC CAPTCHA rate-limit spike (postmortem)

**Date:** 2026-07-08 → 2026-07-10 · **Severity:** P2 · **Author:** Dana

## What happened
UHC tightened bot-defense: CAPTCHA now triggers at roughly **30 requests/hour
per IP** (previously ~90). Navigator throughput on UHC collapsed to a third;
flag rate for UHC jumped from 12% to 41% as jobs timed out to voice/queue.

## Response
We do **not** solve CAPTCHAs — automating around a payer's bot defense is a
line we don't cross (and would poison the provider relationship). Mitigation
was capacity-shaped instead:
1. IP pool widened and per-IP scheduling capped at **25 req/hr** with jitter.
2. UHC job batching rewritten to pull all of a member's data in one session
   (mirroring the MetLife pattern) — cut requests/verification 2.3×.
3. Voice capacity temporarily doubled for UHC during the change.

## Outcome
UHC flag rate back to 13% by July 10 evening. Verification latency for UHC
now ~2.1× pre-incident but inside SLA; residual DATA-MISMATCH exceptions from
their nightly accumulators are a separate, pre-existing issue.

## Follow-ups
- Provider-relations request filed asking UHC for API/EDI accumulator access
  (the real fix — the portal was never meant for this volume).
- Rate-limit config moved from code constants to per-payer config with alarms
  on drift between configured and observed limits.
