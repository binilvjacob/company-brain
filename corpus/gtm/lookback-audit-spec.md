---
title: Lookback audit — spec & readout template
team: gtm
doc_type: spec
owner: chris
updated_at: 2026-02-27
entities: [lookback audit]
---
# Lookback audit — spec & readout template

Our best-converting motion: re-run the prospect's recent verifications and
show what a deeper check would have caught. No integration; export only.

## Inputs (from prospect)
Last 500 verifications (or 60 days, whichever is smaller): patient-deidentified
export with payer, plan, verified-on date, procedures planned, and their
denial/write-off ledger for the same period. **We do not accept PHI in audit
exports** — the export template strips names/DOBs/member IDs; if a prospect
sends raw data anyway, it is deleted, logged, and re-requested through the
template (this has happened twice; both times the discipline impressed the
compliance-minded buyer).

## What we run
Each verification re-checked at our depth: frequency history + pooled
buckets, clause risks (MTC, waiting, replacement), COB ordering, downgrade
exposure. Each finding classified: would-have-flagged, would-have-corrected,
matched.

## Readout format (45 min)
1. Coverage & depth comparison (their check vs ours, side by side, 3 example
   patients — their "dread payers" included).
2. **The denial reconciliation:** which of their actual denials map to
   findings we'd have flagged pre-treatment, with dollar totals. This slide
   closes deals; Coastal's $84k/quarter number came from here.
3. What we'd miss too (be honest — clinical-necessity denials are not ours).
4. Pilot proposal with success criteria pre-filled from their own data.

## Rules
Findings are conservative — when our re-run is uncertain, count it as
"matched", not as a win. An audit that oversells creates a pilot that
disappoints.
