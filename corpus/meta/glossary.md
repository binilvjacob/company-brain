---
title: Needletail company glossary
team: meta
doc_type: glossary
owner: priya
updated_at: 2026-07-28
entities: [ARC, STR, CDT, PMS]
---
# Needletail company glossary

**ARC — Accelerated Revenue Cycle.** Our product line: eligibility & benefits
verification (GA), claims submission (beta since June 2026), payment posting
(targeted Q4 2026), denial management (targeted Q1 2027). Long-term: the single
API endpoint for the dental revenue cycle.

**Straight-through rate (STR).** The % of verifications completed end-to-end by
agents with no human touch. July 2026 average: 85.4%. The company-level target
is 92% by Q2 2027. STR and exception AHT are the two numbers our unit economics
live on.

**Exception queue.** Where the ~15% of verifications that agents flag land for
human review. Staffed by 6 RCM specialists. Each item shows the agent's
pre-filled findings with one-click confirm/correct.

**Exception AHT.** Average handle time on an exception. July 2026: 7m40s
(time study: ~3m knowledge lookup, ~2m data entry, ~2m decision).

**Verification.** One patient/plan eligibility & benefits check: coverage
status, annual max remaining, deductible, frequency history for planned
procedures, clauses (missing tooth, waiting periods), COB status.

**PMS.** Practice management system. We write results back into Dentrix, Open
Dental, Eaglesoft, and Curve Hero.

**Navigator.** A portal-navigation worker (browser automation) driven by a
per-payer YAML nav spec. 400+ payer portals covered; the top 7 payers are ~68%
of verification volume.

**Voice agent.** Calls payer IVR lines when a portal can't answer (e.g.
Guardian frequency history). DTMF-first traversal using per-payer IVR maps.

**Write-back.** Posting verified results into the customer's PMS with
idempotency keys and a dry-run mode.

**CDT codes.** Dental procedure codes. Ones that show up constantly here:
D0120 periodic eval, D0150 comprehensive eval, D0210 FMX, D0274 bitewings,
D0330 panoramic, D1110 adult prophylaxis, D1206 fluoride varnish, D4341/D4342
SRP per quadrant, D4910 perio maintenance, D2740 ceramic crown, D7140
extraction.

**Frequency limitation.** Payer rule capping how often a procedure is covered
(e.g. "2 prophylaxis per calendar year"). The single biggest source of
exceptions and eligibility-related denials.

**Missing tooth clause (MTC).** Exclusion for replacing teeth extracted before
the current coverage started. Enforcement varies sharply by payer.

**COB.** Coordination of benefits across two plans; birthday rule for
dependents. Second-biggest exception driver.

**Downgrade / alternate benefit.** Payer pays for the cheaper alternative (e.g.
posterior composite paid as amalgam). Must be surfaced to the practice before
treatment, not discovered on the EOB.

**Straight-through / flagged / resolved_confirmed / resolved_corrected /
escalated_payer_call.** The lifecycle states of a verification.

**Lookback audit.** GTM motion: we re-run a prospect's last 500 verifications
and show what we'd have caught. Converts better than demos.
