---
title: QA rubric & sampling policy
team: ops
doc_type: sop
owner: priya
updated_at: 2026-02-14
entities: [QA, accuracy]
---
# QA rubric & sampling policy

## Sampling
- Payers live < 60 days: **100% dual review** of exceptions.
- Established payers: 2% random sample of straight-through + 5% of exceptions.
- Any `resolved_corrected` where the correction changed patient out-of-pocket
  by >$200: automatic QA review.

## Rubric (per verification, 5 checks)
1. **Coverage status** correct (active/termed/COB order).
2. **Accumulators** correct (annual max remaining, deductible met).
3. **Frequency history** correct for planned procedures.
4. **Clauses surfaced** (MTC, waiting periods, downgrades) where applicable.
5. **Note quality**: decision + reasoning + source. "Portal said so" is not a
   source; name the tab/field or the call ref number.

Score = checks passed / applicable checks. Verification passes at 5/5;
anything else is a defect with a category.

## Defect categories (July 2026 distribution)
frequency-misread 34% · clause-missed 22% · accumulator-stale 18% ·
COB-order 14% · note-quality 12%

## Current numbers
Blended accuracy 95.2% (target ≥95). Straight-through accuracy 97.1%;
exception-resolution accuracy 91.8% — the gap is why note quality and
knowledge access are QA's top theme this quarter.

## Feedback loop
Defects are reviewed 1:1 weekly; patterns (≥3 same-category defects in a week)
get a playbook or SOP update within the sprint. QA owns confirming the doc
actually changed — a coaching conversation without a doc update is how the
same defect returns in a month.
