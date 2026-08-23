---
title: Claims beta — status notes (June–August 2026)
team: product
doc_type: notes
owner: lena
updated_at: 2026-08-16
entities: [claims, beta]
---
# Claims beta — status notes

8 practices live (3 Summit locations, 2 Bright Smile, Lakeview, 2 independent).

## Numbers (week of 2026-08-10)
First-pass acceptance 87.6% (exit bar: 90% for 2 consecutive weeks across all
8). Volume ~340 claims/day. Top rejection causes: attachment format (38%),
subscriber mismatch on COB claims (24%), payer-specific edit gaps (19%).

## What's working
- Claim assembly from PMS ledger is clean; <1% assembly defects.
- The 85/15 pattern transfers: clean claims straight through, edge cases queue
  with reason codes. Specialists picked up claims-queue work with half a day
  of training because the queue mechanics are identical.

## What's not
- Attachment handling: two payers reject our x-ray format intermittently;
  fix in flight (eng, target end of August).
- COB claims need the *verification* COB data at claim time — the integration
  that passes verified COB ordering into claim assembly ships this sprint.
  Until then COB claims are held for review.

## Decision log
- 2026-07-22: beta exit pushed from "end of July" to "when the bar is met."
  We do not GA on a calendar.
- 2026-08-05: added Lakeview (Curve Hero) to beta to prove the rate-limited
  write-back path under claims volume.
