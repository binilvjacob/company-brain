---
title: Payer IVR call script & press-through paths
team: ops
doc_type: sop
owner: marcus
updated_at: 2026-05-30
entities: [IVR, voice agent, Guardian, MetLife]
---
# Payer IVR call script & press-through paths

Used by the voice agents (as IVR maps) and by specialists making manual calls.

## Universal opening
Provider line → provider services → eligibility/benefits. Have ready: practice
TIN + NPI, member ID (redacted in queue view — pull from PMS at call time),
member DOB, procedure codes in question. Ask for a **reference number before
hanging up** — a verbal answer without a ref number is not a verification.

## Press-through paths (verified dates in parentheses)
- **Guardian** (2026-05, menu changed — old path dead-ends): 2 → 1 → 3 →
  say "eligibility" → hold. Avg 8 min.
- **MetLife** (2026-04): 1 → 4 → 2 → enter TIN → hold. Avg 14 min.
- **DDCA** (2026-03): 3 → 1 → 1 → hold. Avg 11 min. Say "representative" to
  skip the benefits-recording upsell.
- **Aetna** (2026-04): 2 → 2 → enter NPI → hold. Call 7–9am ET; avg 6 min in
  window, 22 min midday.
- **UHC** (2026-06): 1 → 3 → 2 → hold. Avg 12 min.
- **Cigna DPPO** (2026-02): 4 → 1 → hold. DHMO: separate number, ask for the
  capitation schedule desk.
- **FEP** (2026-01): 1 → 2 → hold. COB desk is a warm transfer, 20+ min.

## Question phrasing that gets clean answers
- Frequency: "How many D4910 units has this member used in the current benefit
  period, and what is the period — calendar or rolling?"
- Clauses: "Does this plan have a missing tooth clause, and is there a
  continuous-coverage waiver?"
- Always close with: "Is there anything about this plan that commonly causes
  claim denials for these codes?" Reps volunteer gold on this question.

## After the call
Log rep name, ref number, exact wording in the resolution note. If the answer
contradicts the playbook, do not silently trust either — L2 review, and the
playbook gets updated with the ref number as source.
