---
title: Payer playbook — BCBS Federal Employee Program (FEP BlueDental)
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-03-18
entities: [FEP, BCBS, D1110, D2740]
---
# Payer playbook — BCBS Federal Employee Program (FEP BlueDental)

Volume rank: #7 (≈3%, concentrated near federal employment hubs).

## Portal & access
- Stable portal, but **accumulators display in PLAN year, not calendar year,
  for members who carried over from a prior option** — the single FEP gotcha.
  A member who switched options at open season shows plan-year counts that
  look wrong against calendar-year assumptions. Verify the accumulator period
  label before reading numbers.

## Frequency limitations
- **D1110: 3 per calendar year** — more generous than every other top payer
  (everyone assumes 2; the extra covered cleaning is a practice-delighter,
  surface it).
- D4910: 4 per year with perio history; shares no bucket with D1110.
- Crowns (D2740): 7-year replacement clause.

## Benefit structure quirks
- **Standard option has no annual maximum on in-network preventive/basic** —
  practices double-check this constantly because it sounds too good; it is
  plan design, quote it with the option name.
- High option: $2,500 annual max, standard structure.

## Clauses & quirks
- Missing tooth clause: strictly enforced, both options, no waiver.
- COB with active FEHB medical: dental-first ordering questions come up on
  accident-related claims; their COB desk is voice-only and slow (20+ min) —
  batch these.

## Common exception reasons
1. Plan-year vs calendar-year accumulator misreads.
2. "No annual max, really?" re-verification requests.
3. MTC determinations on takeover patients.

## Escalation
Portal → voice (`fep-v1`) → written determination requests by mail (yes, mail;
21-day turnaround; only for disputes).
