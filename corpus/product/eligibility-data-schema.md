---
title: Verification data schema (what a completed verification contains)
team: product
doc_type: spec
owner: lena
updated_at: 2026-03-26
entities: [verification, schema]
---
# Verification data schema

Every completed verification is one structured record. Fields, in the order
practices read them:

## Identity & plan
`member_ref` (PMS patient link — no raw member IDs stored in ARC),
`payer`, `plan_name`, `group_ref`, `plan_type` (PPO/HMO/voluntary/federal),
`effective_date`, `term_date`, `cob_order` (primary/secondary + basis).

## Money
`annual_max_total`, `annual_max_remaining`, `deductible_total`,
`deductible_met`, `accumulator_period` (**calendar | plan-year | rolling** —
the field the FEP and MetLife gotchas live in), `ortho_lifetime_max` when
applicable.

## Procedure answers (per planned CDT code)
`code`, `covered` (yes/no/conditional), `cost_share_pct`,
`frequency_rule` (human-readable, e.g. "4 per rolling 12mo, pooled hygiene"),
`frequency_used`, `next_eligible_date`, `conditions` (charting required,
program flags like Aetna EOB-MAT), `downgrade_to` (alternate benefit code if
any), `clause_risks` (MTC, waiting period, replacement clause with dates).

## Provenance
`sources[]`: each answer carries where it came from — portal field, voice call
(with ref number), or EDI 271 — plus `retrieved_at`. Provenance is why the
exception queue can show specialists *why* the agent believes something, and
it is non-negotiable for QA.

## Status
`straight_through | flagged(reason_code) | resolved_confirmed |
resolved_corrected | escalated_payer_call`, `specialist`, `resolution_note`.

## Design note
The schema is deliberately payer-agnostic: payer weirdness lives in the
frequency_rule strings and clause_risks, not in per-payer fields. That is what
lets one exception queue serve 400+ portals.
