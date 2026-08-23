---
title: Payer playbook — Cigna Dental
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-05-22
entities: [Cigna, DPPO, DHMO, D4910]
---
# Payer playbook — Cigna Dental

Volume rank: #3 (≈11%).

## Portal & access
- **Two portals: DPPO and DHMO are split.** The member ID format does not tell
  you which; the eligibility API does. Navigators check plan type first and
  route accordingly.
- **DHMO capitation schedules are PDF-only and not machine-readable.** Every
  DHMO verification with procedure-level questions goes to the exception queue
  by design — do not fight this, it is expected behaviour.

## Frequency limitations (DPPO)
- D1110: 2 per calendar year.
- D4910: **2 per calendar year, unless documented perio history, then 4.**
  "Documented" = SRP or perio surgery in claims history with this payer, or
  attached charting from the practice.
- SRP: 1 per quadrant per 24 months.
- Crowns: 5-year replacement clause.

## Waiting periods
- Employer plans: none. Voluntary plans: 6 months on basic services, 12 on
  major.

## Clauses & quirks
- Perio history from *another payer* does not auto-qualify the 4x D4910 rule —
  needs charting upload. Common correction on takeover plans.
- COB: Cigna processes as secondary only with the primary EOB attached; their
  portal COB flag is reliable.

## Common exception reasons
1. DHMO capitation questions (expected, by design).
2. D4910 2-vs-4 perio-history qualification.
3. Takeover plans missing prior perio documentation.

## Escalation
DPPO: portal → voice (`cigna-v4`, avg 9 min). DHMO: voice only for
procedure-level coverage. Provider services fax for charting submissions —
yes, fax; log the confirmation number.
