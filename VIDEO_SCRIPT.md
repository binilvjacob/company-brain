# 3-minute walkthrough — script & shot list

One take, screen + voice, no intro card. Do two dry runs first. Every line
below is against the live URL; keep the browser at 100% zoom, close other
tabs.

**0:00–0:20 — the frame.** *Home screen (Ask tab).*
"Needletail's cost structure lives in the 15% of verifications that need a
human — and almost every human touch is a knowledge lookup. I built the
Company Brain around that: one place where knowledge lives, gets queried to do
work, and where anyone can build tools on top."

**0:20–0:50 — cited answer + freshness.** *Type:* `Does Delta Dental of
California count perio maintenance against the cleaning frequency limit?`
"Every claim is cited. This one's interesting — the SOP still says the old
pooled rule, but DDCA changed it in May. The Brain prefers the newer source,
says the rule changed, and cites both." *Click a citation → source panel.*
"Click through and you're reading the actual playbook section."

**0:50–1:05 — the refusal.** *Type:* `What are Humana's eligibility
verification quirks?`
"No Humana playbook exists — so it says 'I don't know', logs the gap, and
routes it to the ops lead. Silent wrong answers are the exact failure mode
Needletail's founders built the human loop to prevent; the Brain refuses by
design." *Flash the Gaps tab — the question is there, counted.*

**1:05–1:55 — Exception Triage Assist.** *Recipes → Exception Triage Assist.
Fill: payer `Delta Dental of California`, procedure `D4910`, flag reason
`frequency history conflict`.*
"This is the headline: paste a flagged verification and the Brain returns the
governing rule — and the most similar *past resolutions*, what the specialist
decided and why. That's the queue running on the company's own memory."
*Open "Resolve & Teach the Brain", fill decision + reasoning, submit.*
"One click, and that resolution is now retrievable — with provenance."
*Back to Ask, re-ask a matching question, point at the new citation.*
"That's the loop. The exception queue trains the Brain."

**1:55–2:35 — build a tool live.** *Recipes → New recipe.*
"Third clause of the brief: any team member builds tools. Five fields, no
code." *Create "Competitor one-pager": input `competitor`; query
`{competitor} positioning objections pricing case study`; team filter `gtm`;
prompt asking for a cited brief. Save → run it on `VerifyIQ`.*
"Saved, shareable URL, and it's an API endpoint too — same rails for
engineers and everyone else."

**2:35–3:00 — proof.** *README eval table on screen.*
"It's measured: recall, groundedness, refusal accuracy on a golden set —
including the failure modes, like the ranking bug the eval caught. The 90-day
version feeds captured resolutions into the verification agents themselves.
The metric this moves is straight-through rate."

*End on the Gaps dashboard.* "The Brain also knows what it doesn't know —
ranked by how often someone asked. That's where I'd start Monday."
