---
title: Payer playbook — Guardian
team: ops
doc_type: playbook
owner: priya
updated_at: 2026-06-02
entities: [Guardian, D4910, D1206]
---
# Payer playbook — Guardian

Volume rank: #6 (≈5%).

## Portal & access
- **The portal exposes no frequency history at all** — only plan provisions.
  Any verification that needs history (most D4910, replacement-clause work)
  requires a voice call. Guardian is our single largest driver of voice-agent
  minutes; this is structural, not a bug.
- Portal provisions data itself is accurate and fast.

## Frequency limitations
- D1110: 2 per calendar year. D4910: 4 per calendar year with perio history —
  but remaining counts are voice-only (see above).
- **Fluoride varnish (D1206) covered to age 18** (most payers stop at 14) —
  pediatric-heavy practices love this; make sure it lands in the verification
  note.

## Waiting periods
- Voluntary plans: 6-month basic / 12-month major, strictly enforced.

## Clauses & quirks
- **Missing tooth clause: strictest of our top payers.** Enforced on all plan
  types, no continuous-coverage waiver. Extraction date drives it; if the
  member can't date the extraction, treat as MTC-risk and say so in the note.
- COB: birthday rule, portal flag reliable.

## Common exception reasons
1. Anything needing frequency history (voice-only) — expected volume.
2. MTC on takeover patients with undocumented extraction dates.

## Escalation
Voice first for history (`guardian-v1`, avg 8 min, IVR path documented in the
call script — their menu changed 2026-05, old path dead-ends). Provider
services for written MTC determinations.
