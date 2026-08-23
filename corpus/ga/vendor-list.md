---
title: Vendor & tooling list
team: ga
doc_type: notes
owner: maya
updated_at: 2026-05-20
entities: [vendors, tooling]
---
# Vendor & tooling list

What we pay for, who owns it, and the BAA status where PHI could touch it.
New tools: Maya pre-approval + security review before purchase (expense
policy).

## Core / PHI-adjacent (BAA required and in place)
- **Cloud infrastructure (primary)** — owner: Nakul. BAA signed.
- **Telephony/voice platform** — owner: Tomás. BAA signed (call recordings).
- **LLM API provider** — owner: Nakul. BAA-covered endpoints only; model
  training on our data disabled by contract.
- **Error monitoring** — owner: Dana. BAA signed; payload scrubbing on.

## Business tools (no PHI permitted)
- CRM — owner: Chris. Prospect data only; audit exports are de-identified by
  template.
- HR & payroll (India + US EOR) — owner: Maya.
- TravelPerk — owner: Maya.
- Slack, Google Workspace, Notion — owner: Maya. **PHI is prohibited in all
  three**; the exception-queue tool is the only place case detail lives.
  Pasting portal output into Slack is the recurring violation to police —
  see the compliance overview for the redaction rule.

## Renewal calendar
Majors renew in Q1 (infra, telephony) and Q3 (CRM, HR). Maya sends 60-day
notices; owners must re-justify anything above $10k/yr at renewal.
