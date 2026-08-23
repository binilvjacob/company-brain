---
title: Payer playbook — UnitedHealthcare Dental (UHC)
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-07-12
entities: [UnitedHealthcare, UHC, D0330, D0210, D1110]
---
# Payer playbook — UnitedHealthcare Dental (UHC)

Volume rank: #5 (≈8%).

## Portal & access
- **CAPTCHA triggers above ~30 requests/hour per IP.** Navigator fleet rotates
  IPs at 25 requests/hour since INC-2026-055 (July 2026 spike). If you see
  CAPTCHA-blocked flags in the queue, the rotation config has drifted — page
  eng, don't grind through manually.
- Portal accumulators update nightly, not real-time. Same-day treatment
  questions: use voice.

## Frequency limitations
- D1110: 2 per rolling 12 months.
- **Panoramic (D0330) and FMX (D0210) share one bucket: either one per 36
  months, not both.** The portal displays them as separate line items, which
  reads as two separate allowances — it is not. #1 UHC correction in the queue.
- Bitewings: 2 sets per 12 months (their quirk: more generous than most).

## Clauses & quirks
- Downgrades: aggressive on posterior composites (D2392→D2150 alternate
  benefit) on nearly all plans; quote patient out-of-pocket accordingly.
- Missing tooth clause: standard enforcement; portal flag reliable.
- COB: UHC portal auto-hides other-coverage data; ask the member's primary
  first, or the voice line will read it.

## Common exception reasons
1. D0330/D0210 shared-bucket misread.
2. CAPTCHA-blocked navigator runs (ops signal of infra drift).
3. Nightly-accumulator staleness on same-day treatment.

## Escalation
Portal → voice (`uhc-v5`, avg 12 min). No email channel worth using; their
secure-message SLA is 10 business days.
