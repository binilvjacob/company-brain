---
title: ARC platform PRD — eligibility & benefits verification
team: product
doc_type: prd
owner: lena
updated_at: 2026-02-08
entities: [ARC, verification, PMS]
---
# ARC platform PRD — eligibility & benefits verification (GA module)

## Problem
Front desks and RCM teams spend 15–40 minutes per patient confirming coverage
across payer portals and phone calls, or they skip it and eat the denial.
Eligibility-related denials run 8–12% industry-wide; our customer target is
**under 5%**.

## What the product does
For every upcoming appointment (synced from the PMS schedule), ARC produces a
completed verification: coverage status, annual max remaining, deductible,
frequency history for planned procedures, clause risks (MTC, waiting periods,
downgrades), and COB ordering — written back into the PMS before the patient
arrives.

## How
Multi-agent pipeline: navigators traverse 400+ payer portals; voice agents
call payer IVRs when portals can't answer; a resolver merges sources and
computes procedure-level answers; write-back posts to Dentrix, Open Dental,
Eaglesoft, or Curve Hero.

## The 85/15 contract
Agents complete ~85% straight-through. The rest flag into the exception queue
where RCM specialists confirm/correct pre-filled findings. Design principle
from the founders: **AI makes mistakes silently — the system must never guess
where a human should decide.** Every flag carries the reason and the raw
source output.

## Success metrics
- STR ≥ 92% by Q2 2027 (85.4% July 2026)
- Blended accuracy ≥ 95% (95.2%)
- Eligibility-related denial rate at customers < 5%
- Verification completed ≥ 24h before appointment for ≥ 90% of schedule

## Out of scope for this module
Claims submission (own module, beta), patient cost estimates presented to
patients (practice-facing only today), medical-dental cross-billing.
