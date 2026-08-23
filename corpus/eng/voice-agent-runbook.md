---
title: Voice agent runbook
team: eng
doc_type: runbook
owner: tomas
updated_at: 2026-04-19
entities: [voice agents, IVR, DTMF]
---
# Voice agent runbook

## Normal operation
Fleet of concurrent call workers. Each call: dial from the payer's IVR map →
DTMF-first traversal → hold detection (music/silence classifier) → rep
conversation → answer extraction with confidence scores → transcript +
recording attached to job provenance.

## Health signals
- **Traversal success rate** per payer (target ≥97%). A drop means the IVR
  menu changed — regenerate the map from the latest full-menu recording, do
  not hand-patch (Guardian 2026-05 menu change is the case study).
- **Hold-time p50/p95** per payer — feeds the ops scheduler windows (e.g.
  Aetna mornings).
- **Extraction confidence distribution** — a leftward shift usually means a
  new rep script or line quality, not a model problem; listen to 3 calls
  before touching thresholds.

## Common incidents & fixes
- IVR map dead-end: flip payer to `manual-dial` (specialists take over),
  re-map, canary 10 calls, restore.
- Carrier blocks our outbound CLI: rotate the number block, file with the
  telephony provider, expect 24-48h.
- Rep refuses to talk to an automated system: agent discloses on request and
  offers a warm handoff to a specialist; per-payer disclosure scripts live in
  the ops IVR call script doc. Track refusal rate per payer.

## Escalation
Pager: voice-agent oncall (Tomás primary). Anything that changes what we tell
a customer (wrong accumulators from a bad extraction) is a P1 with QA in the
loop, same as a navigator extraction bug.
