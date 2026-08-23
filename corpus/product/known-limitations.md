---
title: Known limitations & workarounds (customer-safe wording inside)
team: product
doc_type: notes
owner: lena
updated_at: 2026-08-09
entities: [limitations]
---
# Known limitations & workarounds

The honest list. Customer-safe phrasing in quotes where CS should use it.

1. **DHMO capitation schedules (Cigna and others).** PDF-only, not
   machine-readable; procedure-level DHMO questions always route to
   specialists. *"DHMO plans are verified with human review included."*
2. **Same-day accumulator freshness on nightly-batch payers (UHC pattern).**
   Portal counts can be a day old; we voice-verify same-day treatment.
   *"Same-day appointments are verified by phone for exact remaining
   benefits."*
3. **Payer portal drift.** Portals change without notice; navigator repairs
   take hours to a day (see eng postmortems). During drift, affected
   verifications degrade to voice + queue. STR dips are visible in the
   customer dashboard.
4. **Medicaid / state programs not supported** (incl. Denti-Cal). On the
   long-term list; not roadmapped. CS: do not commit dates.
5. **Ortho lifetime maximums across payer changes.** Prior-payer ortho usage
   is often unobtainable; we flag rather than guess.
   *"Ortho history from previous carriers is confirmed with the payer
   directly."*
6. **Non-English payer reps.** Voice agent handles English IVRs/reps only;
   others hand to specialists.
7. **Write-back to Curve Hero is API-rate-limited** (their limit): batches
   post in 5-minute windows; "instant" write-back expectation needs setting at
   onboarding.

## Not limitations (things prospects assume we can't do)
Frequency history math across pooled buckets, rolling vs calendar periods,
clause detection (MTC/waiting/replacement), COB ordering — these are core and
differentiating; see the GTM objection doc for proof points.
