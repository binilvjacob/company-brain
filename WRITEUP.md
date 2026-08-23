# The Needletail Company Brain — writeup

**Binil V Jacob · Founder's Office take-home**

## TL;DR

- I built a working Company Brain: ingest → cited answers with honest refusals
  → a no-code Recipe layer where any team member builds tools → a capture loop
  that recycles every resolved exception back into the Brain.
- The one insight everything follows from: **the most valuable knowledge at
  Needletail is generated hourly by the exception queue and then thrown away.**
  The Brain is the memory layer of your human-in-the-loop.
- Live app: **{LIVE_URL}** · Repo: **{REPO_URL}** (`docker compose up` works
  from scratch; `make eval` reproduces the numbers below).
- Measured, not vibes: Recall@5 **{RECALL}**, groundedness **{GROUND}**,
  refusal accuracy **{REFUSAL}** on a 31-question golden set — failure modes
  listed in §6.
- Headline demo: **Exception Triage Assist** — paste a flagged verification,
  get the governing rule plus the two most similar past resolutions and a
  suggested decision, then one click teaches the Brain the outcome.

## 1. How I framed the problem

Needletail's unit economics reduce to two numbers: what fraction of
verifications need a human (15% today), and how long each human touch takes
(7m40s). Nearly every one of those touches is, structurally, a knowledge
lookup — *does DDCA still pool D4910 with cleanings? what did we decide last
time Guardian hid the frequency history?* Your own time-study shape says ~38%
of exception handle time is lookup, and the knowledge being looked up lives in
specialists' heads, Slack scrollback, and a payer-notes sheet. It is generated
fresh every day and discarded every night.

So I scoped the brief's "one place where knowledge lives" as internal
knowledge infrastructure for every team — GTM, product, eng, G&A ride the same
rails — but the strategic reason to build it is the exception queue. Serve
answers fast; capture every resolution as durable, citable memory; route every
unanswered question to an owner. That closes a loop: better Brain → faster
human touches → captured resolutions → richer Brain → and eventually agents
that read the same memory → fewer exceptions. **That is how 85%
straight-through becomes 92% without retraining a model.**

One founder constraint shaped the whole design. "AI makes mistakes silently"
is the reason Needletail keeps humans in the loop — so a Company Brain that
confidently invents a frequency limitation would be worse than no Brain. Every
answer here either carries citations into real sources or is an explicit
refusal that becomes a logged, owner-routed gap.

## 2. What I built, deferred, and rejected

| Built | Why |
|---|---|
| Hybrid retrieval (lexical + vector, RRF, metadata boosts) | The domain is codes and proper nouns; semantic search alone confuses Cigna with MetLife |
| Cited answers + calibrated refusal + gap logging | The founder's stated failure mode, encoded as a system property |
| Recipes + no-code builder + Brain API | The brief's third clause is a platform ask, not a feature ask |
| Capture loop ("Teach the Brain", gaps dashboard) | The compounding mechanism; ~150 lines that turn an artifact into a system |
| Eval harness with golden set | Without a baseline, "retrieval improved" is a feeling |
| Synthetic 114-object corpus with planted contradictions, restricted docs, and real gaps | The demo is only as honest as the questions it can fail |

| Deferred | Why |
|---|---|
| Live Slack/Notion/Drive connectors | A day of OAuth plumbing reviewers can't see; the `SourceAdapter` interface + a typed Notion stub shows the seam (a real connector is a ~50-line file) |
| Auth/SSO | Doc-level `visibility` tags + a role switcher demonstrate permission thinking in 20 lines |
| Feedback ranking (thumbs up/down retraining) | Needs real usage data to be honest |

| Rejected | Why |
|---|---|
| LangChain / LlamaIndex / RAG SaaS | I'd be explaining their retrieval decisions instead of mine |
| Agent frameworks, fine-tuning | Wrong tools for a knowledge substrate; complexity without insight |
| A second datastore (dedicated vector DB) | Postgres does rows, full-text, and vectors in one `docker compose up` |

## 3. Architecture

```
corpus/adapters ─→ KnowledgeObject ─→ redact ─→ chunk (title>heading prefix)
                                                   │ embed
                       Postgres 16 + pgvector + tsvector (one database)
                                                   │
                          lexical (websearch→OR fallback) ─┐
                                                           ├─ RRF ×(1+fresh+authority+team)
                          vector (cosine) ─────────────────┘
                                                   │  visibility hard-filter
                            /ask ─→ cited answer + staleness warnings
                                └─→ confidence gate ─→ refuse ─→ gaps (routed)
                            /recipes/{slug}/run ─→ Recipes ─→ Recipe Builder
                            "Teach the Brain" ─→ /ingest (provenance) ─→ loop
```

Two choices worth defending. **Lexical search is load-bearing here**: the
vocabulary is D4910, Eaglesoft, "FEP" — exact tokens that pure embedding
search genuinely fumbles (it will hand you the MetLife playbook for a Cigna
question). And **freshness/authority are multiplicative tie-breakers, not
additive scores** — my first version added them, which let fresh-but-irrelevant
docs outrank correct answers; the eval caught it (§6).

Every chunk is embedded with a `{doc title} > {section heading}` prefix, so
"limit is 2 per calendar year" is retrievable as *DDCA > Frequency
limitations*. Cheapest quality win in the build.

## 4. The three layers against your brief

**"One place where this knowledge lives."** 114 knowledge objects across
ops/product/eng/GTM/G&A from four source shapes (markdown, CSV sheets, a Slack
export, a typed Notion stub), normalized into one `KnowledgeObject` with
owner, freshness, visibility, and provenance. PHI-shaped fields are stripped
at ingest by a redaction pass.

**"Can be queried to get work done."** Ask in plain English; every claim is
cited [1][2] and clickable through to the source chunk; conflicting sources
are resolved toward the newest with the conflict surfaced (the seeded corpus
contains a real one: DDCA unpooled D4910 from cleanings in May 2026, and the
stale SOP still says otherwise — the Brain answers with the new rule and cites
both). Below the confidence gate it says "I don't have this," logs the gap,
and routes it to the likely owner — the Gaps dashboard is "what this company
most needs to write down, ranked by how often someone asked."

**"Any team member can build small tools on top."** A Recipe is a saved,
shareable mini-tool: inputs + retrieval template + prompt. The Builder is a
five-field form; saving yields `/r/{slug}` in the UI and `POST
/recipes/{slug}/run` on the API — the same rails, so "tools on top" is true
for engineers and non-engineers alike. Three ship pre-built: Payer Playbook
Lookup, **Exception Triage Assist** (retrieves the governing rule *and* the
most similar past resolutions with what the specialist decided — your 15%
queue, made faster with your own memory), and a GTM Objection Responder to
prove the rails are company-wide.

## 5. The capture loop (the part nobody asked for)

Every Triage Assist result ends with **Teach the Brain**: one click turns the
specialist's decision + reasoning into a `KnowledgeObject` with provenance
(who, when, which case), redacted, embedded, and retrievable by the next
specialist *immediately* — the loop closes live in the demo. Refusals feed the
same flywheel from the other side as routed gaps. This is the difference
between a search tool and infrastructure that compounds: the exception queue
trains the Brain, and the Brain is the on-ramp to feeding resolved knowledge
into the verification agents themselves.

## 6. How I know it works — and where it fails

31 golden questions written before tuning (25 answerable across all five
teams, 6 that must be refused — including a visibility trap asked at the
wrong role). `make eval` reproduces this table:

| Metric | Value |
|---|---|
| Recall@5 | {RECALL} |
| Answer rate (answerable) | {ANSWER_RATE} |
| Groundedness (LLM-judged) | {GROUND} |
| Refusal accuracy (unanswerable) | {REFUSAL} |
| p50 latency | {P50} ms |
| Mean cost/query | ${COST} |

Failures and honest notes:

- **My first ranking formula was wrong.** Additive freshness/authority boosts
  swamped RRF's tiny dynamic range and floated fresh-but-irrelevant docs to
  the top; mock-mode Recall@5 went 0.68 → 0.88 when I made boosts
  multiplicative tie-breakers. The eval harness caught it; without a baseline
  I would have shipped it.
- **The refusal gate is two mechanisms, not one.** The confidence gate catches
  off-topic questions cheaply, but topic-adjacent unanswerables (Humana — a
  payer we have no playbook for) survive retrieval and must be refused by the
  grounding contract at generation time. The threshold sweep in the eval
  output is how I picked the operating point ({THRESHOLD}).
- {FAILNOTE}
- Latency is dominated by generation, not retrieval; retrieval is a few ms on
  this corpus and stays sane at 100× with the same Postgres.

## 7. PHI & compliance posture

Unprompted, because this is healthcare: the Brain stores **rules and
resolutions, never patient data**. A redaction pass at ingest strips labeled
patient fields, member IDs, DOBs, SSNs, and phone numbers (demonstrated in the
corpus — one resolution row arrives with fake identifiers and lands clean);
doc-level `visibility` gates restricted material (comp bands are invisible and
unleakable at non-leadership roles — eval-tested); storage is self-hostable
Postgres; generation can point at BAA-covered endpoints by changing one env
var. Every seeded document is synthetic — payer "rules" included — and the
repo's DATA.md says so explicitly.

## 8. What this becomes in 90 days

Weeks 1–2: real Slack + Notion + Drive connectors behind the existing adapter
interface, and capture wired to the actual exception queue tool. Weeks 3–6:
the Gaps dashboard becomes the ops-knowledge backlog with owners and SLAs;
recipes for the top-5 exception reasons (your FREQ-AMBIG class first). Weeks
7–12: the experiment that matters — feed captured resolutions and payer
playbooks into the verification agents' context at run time, measured as an
A/B on flag rate for the treated payers. **The metric this program moves is
straight-through rate; the 90-day target I'd sign up for is +2 points on
treated payers**, with exception AHT as the guardrail metric.

## 9. What I'd want to know from you

1. What's the current average handle time split on an exception — how much is
   lookup vs data entry vs decision — and do you track it per reason code?
2. What are the top 5 exception reasons by volume? (Those are the next five
   recipes.)
3. Where does payer knowledge actually live today — sheet, heads, or encoded
   in the portal adapters — and who updates it when a payer changes a rule
   mid-year?
4. Do specialists' resolutions feed back into the agents at all today, or is
   every verification stateless?
5. As claims → posting → denials ship, does knowledge grow linearly, or does
   denial management need a different shape (appeal letters are documents,
   not lookups)?
