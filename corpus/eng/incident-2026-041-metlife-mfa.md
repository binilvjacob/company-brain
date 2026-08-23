---
title: INC-2026-041 — MetLife MFA rotation breaks navigator auth
team: eng
doc_type: runbook
owner: dana
updated_at: 2026-06-05
entities: [MetLife, MFA, INC-2026-041]
---
# INC-2026-041 — MetLife MFA rotation breaks navigator auth (postmortem)

**Date:** 2026-06-01 → 2026-06-02 · **Severity:** P2 · **Author:** Dana

## What happened
MetLife moved MFA secret rotation from quarterly to **monthly on the 1st**
without notice. All MetLife navigator sessions began failing auth at 06:10 ET
on June 1. Conductor flipped MetLife voice-first after 3 failures (as
designed), so no wrong data shipped — but voice capacity saturated, MetLife
verifications backed up ~5 hours, and 2 practices missed the 24h-before-
appointment target.

## Timeline
06:10 auth failures begin · 06:18 canaries page oncall · 06:40 voice-first
confirmed active · 09:30 root cause identified (rotation policy change,
confirmed with MetLife provider support) · 13:00 credential re-enrollment
automated for all offices · 14:45 canaries green, portal-first restored.

## Root cause
We treated MFA secrets as quarterly-static. The payer changed the contract.

## What we changed
1. Credential job now **re-enrolls proactively on the 1st of every month** for
   any payer observed rotating monthly (MetLife today), before business hours.
2. Rotation-policy drift detection: an auth failure whose error class is
   "expired factor" opens a credential ticket automatically instead of a
   generic drift ticket.
3. Ops playbook updated: 1st-of-month MetLife failures are expected until the
   job finishes (~05:30 ET); do not manually grind the portal.

## What we deliberately did not do
Store backup codes to bypass MFA — rejected on security grounds; slower
re-enrollment is the right trade.
