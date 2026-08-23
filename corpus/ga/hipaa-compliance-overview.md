---
title: HIPAA & data-handling compliance overview
team: ga
doc_type: policy
owner: maya
updated_at: 2026-04-08
entities: [HIPAA, BAA, PHI]
---
# HIPAA & data-handling compliance overview

We operate as a **business associate** to dental practices (covered
entities). Plain-language summary; the formal policy set lives with counsel.

## The agreements
- **BAA with every customer** before any PHI flows — no pilot starts without
  it (including lookback audits, which use de-identified exports precisely so
  the audit can precede deep integration).
- BAAs with every downstream vendor that could touch PHI (see vendor list:
  infra, telephony, LLM endpoints, error monitoring).

## Data minimization rules (the ones everyone must know)
1. Raw member identifiers live in transient job scope and the customer's PMS;
   our long-term stores keep `member_ref` links only.
2. **PHI is prohibited in Slack, email, Notion, and the CRM.** Case discussion
   happens in the queue tool. If you must reference a case elsewhere, use the
   case ID. Pasted portal output is the recurring violation — redact before
   pasting, and report accidental pastes to Maya (deletion + log, no blame
   first time, pattern gets training).
3. Access is role-scoped; specialists see their queue, not the firehose.
   Access reviews quarterly.
4. Call recordings auto-purge at 90 days unless QA-flagged.

## Incident duty
Suspected PHI exposure → Maya + Nakul same day, no exceptions, no
self-triage. Breach-notification clocks are legal timelines, not judgment
calls.

## Training
HIPAA onboarding module in week 1, annual refresh, ops gets the extended
portal-data-handling module. Completion tracked; overdue training blocks
queue access.
