# Data statement — read this first

**Every document in `corpus/` is synthetic.** I wrote it for this prototype so the
Brain has a realistic, internally consistent body of Needletail-shaped knowledge
to retrieve against. Specifically:

- **No PHI, anywhere.** No document contains real patient names, DOBs, member IDs,
  or any real person's health information. A few documents include *synthetic,
  clearly fake* labeled fields precisely so the ingest-time redaction pass
  (`app/redact.py`) has something to demonstrably strip.
- **Payer rules are invented.** Frequency limitations, waiting periods, clause
  behaviours, and portal quirks attributed to real payer brands (Delta Dental of
  California, MetLife, Cigna, etc.) are plausible-sounding fabrications for demo
  purposes — they are **not** real payer policy and must not be used for actual
  verification work.
- **People are fictional** — every employee named in the corpus (Priya, Marcus,
  Anika, Dana, Lena, Chris, Maya, Tomás, Rohan) is invented. The founders (Jofin
  Joseph, Nakul Sibiraj) appear only as document owners, with content paraphrased
  from Needletail's public materials.
- **Customers and competitors are fictional.** "Summit Dental Partners",
  "VerifyIQ", "DentaCheck" and the rest do not exist; any numbers about them are
  invented.
- **Seeded demo rows are labeled.** Three rows in the Gaps dashboard are
  pre-seeded (marked `demo seed` in the UI and `source='seeded-demo'` in the DB)
  so the dashboard tells its story on first click; everything else in that table
  comes from live refusals.

## PHI posture for a real deployment

The Brain stores **rules and resolutions, never patient data**: patient
identifiers are stripped at ingest by the redaction pass, storage is
self-hostable Postgres, generation can run against BAA-covered LLM endpoints,
and doc-level `visibility` tags gate restricted material. See the "PHI &
compliance posture" section of WRITEUP.md.
