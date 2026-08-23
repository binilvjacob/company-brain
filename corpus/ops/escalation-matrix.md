---
title: Exception escalation matrix
team: ops
doc_type: sop
owner: priya
updated_at: 2026-05-05
entities: [escalation, exception queue]
---
# Exception escalation matrix

Ladder for a flagged verification. Each rung has an owner and a time budget;
"stuck" means the rung's budget is spent without a defensible answer.

## L1 — Specialist (budget: 7 minutes)
Playbook + portal + resolution search. Most items end here as
`resolved_confirmed` or `resolved_corrected`. If your answer relies on memory
rather than a source you can cite, you are not done — find the source or
escalate.

## L2 — Senior specialist (Marcus) (budget: 15 minutes)
Cross-payer weirdness, COB ordering disputes, anything where playbook and
portal genuinely conflict after the L1 workaround list is exhausted.
L2 owns updating the payer-notes sheet when the resolution reveals a new quirk.

## L3 — Payer voice call
Placed by the voice agent when possible (IVR map exists + question is
history/accumulator shaped), else manually. Always capture: rep name, ref
number, exact wording. A verbal answer without a ref number is not a
verification.

## L4 — Account escalation (Priya)
Customer-visible risk: same-day appointment at risk, repeated payer failure
affecting one practice, anything a practice manager has already emailed about.
Priya owns the customer comm; specialist stays owner of the verification.

## Eng ticket (parallel, not a rung)
If the root cause is ours — navigator drift, truncated portal output, write-back
mismatch — file `#eng-incidents` with the run ID. Dana owns portal adapters,
Tomás owns voice. Do not hold the verification for the fix; resolve via voice
and let eng fix the automation.

## Priority lane
Same-day appointments: 30-minute SLA, skip L1→L2 queueing, straight to the
fastest source of truth (usually voice). Flagged automatically by appointment
date; can be flagged manually from the queue.
