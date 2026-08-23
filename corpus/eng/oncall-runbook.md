---
title: On-call runbook (eng)
team: eng
doc_type: runbook
owner: nakul
updated_at: 2026-06-07
entities: [oncall, incidents]
---
# On-call runbook (eng)

Rotation: weekly, two seats (platform, agents). Handoff Mondays with a written
summary in #eng-incidents.

## Severity ladder
- **P1** — wrong data could reach a customer (bad extraction passing gates,
  write-back defect), or verification pipeline down for a top-7 payer.
  Page immediately, QA in the loop, customer comms via Priya if any practice
  is affected. Postmortem required.
- **P2** — a payer degraded (portal drift, voice dead-end) with fallback
  working. Business-hours fix; ops informed in #eng-incidents.
- **P3** — everything else.

## First moves by symptom
- Flag-rate spike for one payer → check canary history & nav spec version;
  9 of 10 times it's portal drift; flip voice-first if assertions failing.
- Write-back errors → check PMS API status first (Curve rate limits, Dentrix
  maintenance windows Sunday nights), then idempotency-key collisions.
- Queue filling faster than specialists clear → confirm it's real volume vs a
  flag storm (one bad spec can flag everything); flag storms get the spec
  rolled back, not more specialists.
- MFA/auth failures on the 1st of the month → MetLife rotation; run the
  credential job, see INC-2026-041.

## Invariants (do not "fix" around these)
1. Below-confidence data never writes back — no manual overrides in prod.
2. Provenance log is append-only.
3. A payer with failing canaries stays voice-first no matter the backlog.
