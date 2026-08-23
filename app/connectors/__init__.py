"""Live connectors — streams in, not files in.

The batch adapters (app/adapters/) prove "knowledge lives here" on exported
files. Connectors prove it on live streams: no exports, no uploads, no one
doing anything manually. Two shapes exist:

- push (webhook): the source calls us on every event. Telegram ships first —
  it is the same mechanism as WhatsApp (chat -> webhook -> ingest) minus
  Meta's business-verification queue, so it stands in for WhatsApp honestly.
  Slack's Events API is the same shape and is next.
- pull (poll): we fetch deltas on a schedule. The keepwarm cron already hits
  the app every 10 minutes; pointing it at POST /sync/run gives free-tier
  scheduled sync with no new infrastructure. Drive/Gmail slot in here.

Every connector is a *client of the same ingest pipeline* as every adapter:
redact -> chunk -> embed -> visibility. Connectors decide what enters and
with how much trust (ambient chat is low-authority, human-vouched capture is
higher); they never get their own retrieval path. One brain, many mouths.
"""
