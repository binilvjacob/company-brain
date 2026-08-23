---
title: Exception handle-time study — July 2026
team: ops
doc_type: notes
owner: priya
updated_at: 2026-07-21
entities: [AHT, exception queue]
---
# Exception handle-time study — July 2026

Method: 240 exceptions sampled across 6 specialists over two weeks, screen
timing by phase. Third study in the series (Jan 2026: 8m50s; Apr 2026: 8m05s).

## Headline
**Average handle time: 7m40s** per exception. At ≈1,340 exceptions/day that is
~171 specialist-hours/day of queue work.

## Phase breakdown
- **Knowledge lookup: 2m55s (38%)** — playbook reading, sheet searching,
  Slack scrollback, asking a neighbour. The most variable phase: 40s when the
  specialist "just knows", 6m+ on unfamiliar payer/procedure pairs.
- **Data entry / correction: 2m05s (27%)** — fixing pre-filled fields,
  PMS cross-checks.
- **Decision + note writing: 1m50s (24%)** — includes the resolution note.
  Note quality correlates inversely with time pressure; rushed notes are the
  #1 QA note-quality defect source.
- **Waiting / context switching: 50s (11%)** — portal loads, queue refresh.

## Observations
1. Knowledge lookup is the biggest and most compressible phase. Specialists
   with <6 months tenure spend 2.3× longer here than veterans; the gap IS the
   undocumented knowledge.
2. 31% of lookups ended in a Slack search or asking someone — knowledge that
   exists but isn't findable in a playbook.
3. Veterans resolve repeat patterns from memory. That memory leaves when they
   do.

## Implication
Cutting lookup from ~3m to ~1m at current volume frees ≈45 specialist-hours/
day — roughly one full-time specialist per shift — before any STR gain.
