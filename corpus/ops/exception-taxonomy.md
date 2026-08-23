---
title: Exception reason taxonomy & July 2026 volume
team: ops
doc_type: sop
owner: priya
updated_at: 2026-08-02
entities: [exception queue, STR]
---
# Exception reason taxonomy & July 2026 volume

Every flag carries exactly one primary reason code. July 2026: ~9,200
verifications/day, STR 85.4%, ≈1,340 exceptions/day.

## Reason codes, by share of exceptions
1. **FREQ-AMBIG (31%)** — frequency history ambiguous or conflicting between
   sources (portal vs voice vs PMS ledger). Biggest single lever on STR.
2. **COB-UNRES (18%)** — dual coverage with unresolved ordering; birthday-rule
   dependents, spouse-plan takeovers.
3. **DATA-MISMATCH (14%)** — portal and voice (or two portal views) disagree on
   accumulators.
4. **MTC-VERIFY (9%)** — missing tooth clause risk needs extraction-date
   evidence.
5. **WAIT-PERIOD (8%)** — new-member waiting-period status unclear (mostly
   voluntary plans: MetLife, Cigna, Guardian).
6. **PLAN-NOTFOUND (7%)** — member ID format issues, takeover groups, plan not
   located in payer system.
7. **DOWNGRADE-AMBIG (6%)** — alternate-benefit applicability unclear.
8. **OTHER (7%)** — everything else; anything reaching 3% gets its own code at
   quarterly review.

## Why the taxonomy matters
Reason codes drive routing (which specialist), the QA sample, and the roadmap
argument for which knowledge to write down next. FREQ-AMBIG being #1 is why
payer playbooks lead with frequency sections, and why the first Brain recipes
are payer lookup and triage assist.

## Trend note (last 90 days)
FREQ-AMBIG down from 35% → 31% after the May DDCA rule change was documented;
COB-UNRES flat; DATA-MISMATCH up 2pts with the UHC nightly-accumulator issue —
eng tracking under INC-2026-055 follow-up.
