---
title: Exception queue SOP v2.3
team: ops
doc_type: sop
owner: priya
updated_at: 2025-12-10
entities: [exception queue, D4910, D1110, Delta Dental of California]
---
# Exception queue SOP v2.3

Scope: how RCM specialists work the exception queue. Owner: Priya. Review
cadence: quarterly (v2.3 approved 2025-12-10).

## Intake
Agents flag a verification when confidence is below threshold or data sources
disagree. Flagged items land in the queue with the agent's pre-filled findings:
coverage status, accumulators, frequency history, the specific reason for the
flag, and raw portal/voice output. Same-day-appointment items enter the
priority lane (30-minute SLA); everything else is 4 business hours.

## Working an item
1. Read the flag reason first, not the whole record.
2. Confirm or correct each pre-filled field. One-click confirm when the agent
   was right; correct inline when it wasn't.
3. Frequency questions: check the payer playbook, then the member's history in
   the portal. Example: for Delta Dental of California, D4910 perio maintenance
   counts against the D1110 prophylaxis frequency — any 2 hygiene visits per
   calendar year combined, so a member with 2 cleanings this year has 0 D4910
   remaining.
4. If portal and voice disagree, voice wins for accumulators, portal wins for
   plan provisions; document both values in the resolution note.
5. Write the resolution note in the decision + reasoning format. The note is
   not paperwork: the next specialist searches these.

## Decisions
- `resolved_confirmed` — agent findings correct as-is.
- `resolved_corrected` — findings corrected; state exactly what changed.
- `escalated_payer_call` — voice call placed or scheduled; capture ref number.

## Quality bar
QA dual-reviews 100% of exceptions for payers live <60 days, 2% sample
otherwise. Blended accuracy target ≥95% (see QA rubric).

## Do not
- Do not guess accumulators. Silent wrong answers are the failure mode this
  whole company exists to prevent — escalate instead.
- Do not resolve from memory of "how this payer usually is" without checking
  the playbook date. Rules change mid-year.
