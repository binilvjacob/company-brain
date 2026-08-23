---
title: Customer dashboard — verification report spec
team: product
doc_type: spec
owner: lena
updated_at: 2026-04-11
entities: [dashboard, reporting]
---
# Customer dashboard — verification report spec

What RCM leaders see. Three views:

## Daily operations view
Per location: schedule coverage (% of tomorrow's appointments verified),
verifications completed, flagged-in-review count with reasons, priority-lane
items and SLA status. Refreshes every 15 minutes.

## Quality view
STR for the account, blended accuracy from QA sampling, denial tracking:
eligibility-related denials as % of claims (target <5%), with drill-down to
the specific verifications behind any denial. This view is why finance renews.

## Exceptions view
Every flagged verification with reason code, current status, specialist,
resolution note (customer-safe fields only), and time-to-resolution against
SLA. Practices asked for visibility, not control: they can comment and mark
urgency, not edit findings.

## Export & API
Nightly CSV to SFTP for DSO data teams; REST read API with per-location keys.
The API mirrors the verification data schema doc — one schema everywhere.

## Deliberate exclusions
No raw member IDs anywhere in the dashboard (member_ref links back into their
own PMS). No specialist names shown to customers (queue metrics are team-level)
after the March incident where a practice manager called a specialist
directly.
