---
title: PMS integration notes (Dentrix, Open Dental, Eaglesoft, Curve Hero)
team: eng
doc_type: notes
owner: nakul
updated_at: 2026-06-21
entities: [Dentrix, Open Dental, Eaglesoft, Curve Hero, write-back]
---
# PMS integration notes

Per-PMS quirks for schedule sync (read) and write-back (write). All four run
idempotent write-back with dry-run mode and per-field audit logs.

## Dentrix
Server-based; we integrate via their API layer where licensed, bridge agent
elsewhere. Maintenance window Sunday nights — write-back queues and drains
Monday 05:00 local. Insurance note fields are length-capped: long verification
summaries auto-truncate with a link back to the full record.

## Open Dental
The pleasant one: open API, real-time both directions. We write structured
benefit fields, not just notes — frequency next-eligible dates land in their
insurance benefit tables directly. Reference integration for demos.

## Eaglesoft
File/DB-level integration through the bridge agent. Slowest read path
(schedule sync every 15 min vs near-real-time elsewhere). See INC-2026-032
for the double-posting postmortem that hardened all four workers.

## Curve Hero
Cloud PMS, clean API but **rate-limited by contract**: batches post in
5-minute windows. Set the "instant write-back" expectation correctly at
onboarding (bit us at Lakeview). Also the only PMS where schedule sync is
webhook-push instead of poll — nicest architecture, least mature API surface.

## Cross-PMS invariants
`member_ref` linking only (no member IDs stored our side), exactly-once
posting by construction, and a practice-visible audit trail of every field we
wrote, when, and from which verification.
