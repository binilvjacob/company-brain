---
title: Why portal scrapes break — drift taxonomy
team: eng
doc_type: notes
owner: dana
updated_at: 2026-05-28
entities: [drift, navigators]
---
# Why portal scrapes break — drift taxonomy

Running tally of every navigator breakage class since GA, because "the portal
changed" hides five different failure modes with five different defenses.

## 1. DOM drift (≈45% of breakages)
Selectors move, IDs regenerate, frameworks re-render. Defense: assertion
landmarks + semantic selectors (label-relative) over brittle CSS paths;
canaries catch it within the hour.

## 2. Auth & session policy changes (≈20%)
MFA rotation schedules (INC-2026-041), session timeout tightening, new device
checks. Defense: credential jobs on payer-observed schedules, session budgets
per payer, error-class-specific tickets.

## 3. Bot defense changes (≈15%)
Rate limits, CAPTCHA thresholds (INC-2026-055), IP reputation scoring. Defense:
per-payer request budgets with jitter, batching per member, and a hard policy
line: we shape capacity, we never bypass bot defense.

## 4. Data format changes (≈12%)
Benefits PDFs restructured, date format flips, accumulator tables renamed.
The nastiest class because pages still load — only schema sanity checks catch
"remaining > total" or unparseable dates before a human sees garbage.

## 5. Content-behaviour bugs on the payer side (≈8%)
The portal is *wrong*, not changed: DDCA's exhausted-banner-with-secondary,
Aetna's 1st-of-month stale groups. Defense: cross-source checks and ops
playbook workarounds; we report upstream and encode the workaround.

## The meta-lesson
Every class ends with the same move: the failure produces a *flag with a
reason*, never a silent wrong answer. Drift costs us throughput; it must never
cost a practice a wrong verification.
