---
title: Payer playbook — MetLife Dental
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-06-19
entities: [MetLife, D4910, D1110, D2740]
---
# Payer playbook — MetLife Dental

Volume rank: #2 (≈13%).

## Portal & access
- **Hard 8-minute session timeout.** Navigators batch all queries for a member
  into one session; if you're working manually, gather your questions first.
- MFA secret rotates monthly on the 1st; expect navigator failures the first
  morning of each month until the credential job runs (see INC-2026-041).

## Frequency limitations
- Hygiene: **4 total hygiene visits per 12 rolling months, D1110 and D4910
  combined** (their "total cleanings" rule). Perio history does not add visits.
- D1110 alone capped at 2 of those 4.
- Bitewings 1/12mo rolling. Crowns (D2740): **7-year** replacement clause.

## Waiting periods
- **Voluntary (member-paid) plans: 12-month waiting period on major services**
  (crowns, dentures, implants). Employer-funded plans typically none. The
  portal's plan-type field says which; if it reads "VOL", check effective date
  vs. treatment date before verifying major work.

## Clauses & quirks
- Rolling 12-month accumulators, not calendar year — the #1 source of
  frequency miscounts when a member switches from a calendar-year payer.
- Missing tooth clause on voluntary plans only.
- Downgrades: plan-dependent; the portal benefit detail names the alternate
  benefit code when it applies.

## Common exception reasons
1. Rolling vs calendar-year frequency confusion.
2. Session-timeout truncation: partial portal output reaches the agent
   (retriggered automatically; flag if second pass also truncates).
3. Voluntary-plan waiting periods on major services.

## Escalation
Portal → voice (IVR map `metlife-v2`, avg 14 min; press-through sequence
documented in the IVR call script). Written confirmations via provider portal
secure message; 3–5 day turnaround, use only for non-urgent disputes.
