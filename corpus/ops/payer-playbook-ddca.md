---
title: Payer playbook — Delta Dental of California (DDCA)
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-08-06
entities: [Delta Dental of California, DDCA, D4910, D1110, D4341, D2740]
---
# Payer playbook — Delta Dental of California (DDCA)

Volume rank: #1 (≈19% of daily verifications). Portal + voice both supported.

## Portal & access
Provider portal sessions are stable; MFA is per-registered-office. Two known
data issues the agents compensate for:
- The benefits summary PDF lags real-time plan changes by 24–48h. If the member
  changed plans this week, trust the eligibility API view, not the PDF.
- A "benefits exhausted" banner appears incorrectly when the member has
  secondary coverage on file. Workaround: open the claims-history tab and check
  actual accumulator postings before trusting the banner. (Bug reported to DDCA
  2026-03; still open.)

## Frequency limitations
**Updated 2026-08-06 following DDCA provider services confirmation
(ref DD-2026-081, see #ops-payer-questions thread of 2026-08-04):**

- **Effective 2026-05-01, D4910 perio maintenance no longer shares a frequency
  bucket with D1110 prophylaxis.** D4910 is separately allowed **4 per 12
  months** when the member has documented SRP (D4341/D4342) within the past 24
  months. D1110 remains **2 per calendar year**.
- Before 2026-05-01 the combined rule applied (any 2 hygiene visits per
  calendar year, D1110 and D4910 pooled). Older SOP examples still describe the
  pooled rule — they are out of date for dates of service after 2026-05-01.
- D0274 bitewings: 1 set per calendar year. D0330 panoramic: 1 per 3 years.
- D2740 crowns: 5-year replacement clause, per tooth, measured from prior seat
  date.

## Clauses & quirks
- Missing tooth clause: **group-contract dependent.** The portal exposes a
  `missingToothProvision` flag per group — always read it; do not assume.
- SRP (D4341/D4342): 1 per quadrant per 24 months; no charting attachment
  required for verification (unlike Aetna).
- Downgrades: posterior composites paid at amalgam rate on most groups.

## Common exception reasons
1. Pre/post-May-2026 D4910 confusion (portal history shows pooled counts for
   older dates of service).
2. "Benefits exhausted" banner with secondary coverage (see above).
3. Plan-change week: PDF vs API mismatch.

## Escalation
Portal data conflict → claims-history tab → if still ambiguous, voice line
(IVR map `ddca-v3`, avg 11 min) → provider services email for written
confirmation. Log written confirmations in the payer-notes sheet with the
reference number.
