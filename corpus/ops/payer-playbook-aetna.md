---
title: Payer playbook — Aetna Dental
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-04-30
entities: [Aetna, D4341, D4342, D2740, D1110]
---
# Payer playbook — Aetna Dental

Volume rank: #4 (≈9%).

## Portal & access
- **1st-of-month cache bug:** the bulk eligibility endpoint serves stale group
  numbers on the 1st (their cache refreshes overnight on the 2nd). Verifications
  run on the 1st for members whose employer changed plans at month boundary
  will show the old group. Navigators re-verify anything group-sensitive dated
  the 1st.
- Voice line hold times: best window 7–9am ET (avg 6 min), worst 12–2pm ET
  (avg 22 min). The scheduler batches Aetna voice calls into the morning
  window.

## Frequency limitations
- D1110: 2 per calendar year; **+1 additional prophylaxis during pregnancy**
  when the member is enrolled in their maternity program (portal flag
  `EOB-MAT`).
- **SRP (D4341/D4342) requires perio charting no older than 6 months attached
  to the pre-treatment estimate** — verification without charting comes back
  "covered, subject to review", which practices misread as a yes. Always
  surface the charting requirement in the verification note.
- Crowns: 5-year clause, measured from **seat date**, and Aetna bills by prep
  date — the mismatch generates spurious "too soon" warnings. Check both dates.

## Clauses & quirks
- Missing tooth clause **waived** if the extraction happened under continuous
  Aetna coverage (any group). Their portal shows continuous-coverage start —
  quote it.
- Downgrades: posterior composite → amalgam on standard plans.

## Common exception reasons
1. SRP charting requirement misread as full approval.
2. Seat-date vs prep-date crown warnings.
3. 1st-of-month stale group numbers.

## Escalation
Portal → voice (`aetna-v2`) in morning window → provider services reference
number for anything charting-related.
