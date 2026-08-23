---
title: Objection handling guide
team: gtm
doc_type: playbook
owner: chris
updated_at: 2026-05-11
entities: [objections, VerifyIQ, EDI]
---
# Objection handling guide

The five we hear weekly. Structure: acknowledge → reframe → proof.

## "We already have offshore VAs doing this."
Reframe to **cost per *correct* verification and turnaround**. VAs run
$3–6/verification fully loaded at 24–48h turnaround with no audit trail; we
run same-morning at tier price with provenance on every field. Do not trash
VAs — many prospects like their team; position as "your team stops doing
lookups and starts doing judgment," which is literally our exception queue.
Proof: Summit case (3.2-day backlog → same-morning; 2 FTEs redeployed).

## "Our clearinghouse already gives us eligibility (EDI 270/271)."
The 271 tells you the plan exists; it does not answer the questions that cause
denials: **frequency history, pooled buckets, clause risks, downgrade
behaviour, COB ordering.** We tried EDI-first ourselves and retired it —
the data is too shallow (feature-flag registry, `edi-first`, retired 2026-04).
Proof: run the lookback audit; the audit report shows exactly which of their
denials a 271 could never have caught.

## "AI will make mistakes silently."
Agree — that is why the founders built the 85/15 model. Walk the queue:
every below-confidence verification flags with a reason, humans decide,
accuracy runs 95%+, and every answer carries provenance (portal field or call
ref). Our whole architecture is organized around never guessing.

## "Writing into our PMS scares us."
Dry-run mode for the first two weeks (they approve every posting), idempotent
writes, per-field audit log, and the practice can see everything we wrote.
Coastal's onboarding is the reference call for a skeptic-turned-advocate.

## "We're too small / too cheap for this."
Check the math honestly: under ~800 verifications/mo the ROI is thin — say so
and stay in touch. Under-selling small practices poisons referrals; the honest
"not yet" wins DSO intros later.
