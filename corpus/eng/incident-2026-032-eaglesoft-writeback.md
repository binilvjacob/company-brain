---
title: INC-2026-032 — Eaglesoft write-back double-posting
team: eng
doc_type: runbook
owner: nakul
updated_at: 2026-04-25
entities: [Eaglesoft, write-back, INC-2026-032]
---
# INC-2026-032 — Eaglesoft write-back double-posting (postmortem)

**Date:** 2026-04-12 · **Severity:** P1 · **Author:** Nakul

## What happened
A retry bug in the Eaglesoft write-back worker posted **duplicate benefit
notes** into 214 patient records across 2 Coastal Dental locations over 6
hours. No clinical or financial fields were affected — the duplicated artifact
was the verification summary note — but duplicates in a chart are a trust
wound at a customer whose pitch from us is "we write into your system of
record safely."

## Root cause
The worker's idempotency key included a timestamp component, so a
timeout-then-retry generated a *new* key and posted again. The dry-run test
suite never exercised the timeout path.

## Fix
1. Idempotency key = hash(verification_id + field_set), no time component.
2. Write-back retries are now **read-verify-then-write**: on retry, the worker
   reads the target record and skips if the content hash is present.
3. Cleanup script removed all 214 duplicates same-day; Coastal received the
   incident summary and the cleanup diff (Priya handled comms).
4. Timeout-path tests added for all four PMS workers.

## Lessons
P1 classification was correct even with "just notes" — the blast surface is
customer trust, not data category. And write-back is the one place where "at
least once" delivery is wrong; everything there must be exactly-once by
construction.
