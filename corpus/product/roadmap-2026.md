---
title: ARC roadmap 2026-2027
team: product
doc_type: prd
owner: lena
updated_at: 2026-06-28
entities: [ARC, claims, payment posting, denial management]
---
# ARC roadmap 2026–2027

North star: from eligibility wedge to the **single API endpoint for the dental
revenue cycle**.

## Shipped / GA
**Eligibility & benefits verification** — GA. 400+ portals, voice agents,
write-back to Dentrix, Open Dental, Eaglesoft, Curve Hero. STR 85.4% and
climbing; the STR-to-92% program is the module's whole 2026 arc.

## In beta — Claims submission (since June 2026)
8 practices in beta. Scope: claim assembly from the PMS ledger, payer-specific
edits, attachment handling, submission via clearinghouse, status tracking.
Design principle carried over: same 85/15 model — clean claims go straight
through, edge cases queue with reasons. Beta exit criteria: 2 weeks at ≥90%
first-pass acceptance across all 8 practices.

## Q4 2026 — Payment posting
ERA/EOB ingestion, line-level posting into the PMS, variance flags when paid ≠
verified expectation. Depends on claims GA. The verification-vs-payment
variance data is strategically important: it closes the loop on whether our
eligibility answers were right.

## Q1 2027 — Denial management
Denial intake, root-cause classification (eligibility, clinical, admin),
auto-generated appeals for the classes we can win, and the feedback loop into
verification rules. Explicit bet: by launch, most eligibility-class denials
should be *preventable* by the verification module — denial management proves
it and mops up the rest.

## Sequencing rationale
Each module generates the data the next one needs: verification →
claim accuracy → posting variances → denial root causes. We do not build
ahead of the data.
