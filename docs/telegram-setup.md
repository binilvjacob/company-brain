# Telegram connector — 5-minute setup

The Brain's first **live** source: a bot sits in your group chat and the chat
becomes part of the knowledge base — no exports, no uploads. (Telegram stands
in for WhatsApp: the mechanism is identical; WhatsApp's Business API just adds
a Meta business-verification queue.)

## 1. Create the bot (2 minutes, in Telegram)

1. Message **@BotFather** → `/newbot` → pick a name (e.g. *Needletail Brain*)
   and a username (e.g. `needletail_brain_bot`). Copy the **token**.
2. Still in BotFather: `/setprivacy` → select your bot → **Disable**.
   ⚠ This step is required — with privacy mode on (the default), bots in
   groups only see `/commands`, so ambient capture would see nothing.

## 2. Configure the deployment (2 minutes, in GitHub)

Repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `CONNECTOR_SECRET` | any random string, e.g. `openssl rand -hex 16` |

Then run the pipeline once (push anything, or Actions → *pipeline* → *Run
workflow*). The deploy job syncs both secrets into Render, and the app
**registers its own webhook at boot** using Render's `RENDER_EXTERNAL_URL` —
there is no manual webhook step. `GET /healthz` shows
`"connectors": {"telegram": true}` when it's live.

## 3. Use it

Create a group, add the bot, and:

- **just talk** — every message is buffered (identifiers PHI-redacted *before*
  storage); once the chat is quiet for 30 minutes, the run is distilled into
  one low-authority `chat_thread` knowledge object (the keepwarm cron flushes
  this every 10 minutes via `POST /sync/run`).
- **`/teach`** — capture the last 20 messages (or `/teach 5`) right now as a
  higher-authority `notes` object with provenance: who taught, which chat,
  which messages. Vouched beats ambient.
- **`/ask <question>`** — a cited answer in the chat, or an honest refusal
  that lands in the Gaps dashboard, routed to an owner.
- **`/team gtm`** — file this chat's knowledge under a different team
  (default `ops`).

## Local dev (no public URL)

```bash
TELEGRAM_BOT_TOKEN=... python scripts/telegram_poll.py
```

Long-polls `getUpdates` and feeds the same handler the webhook uses.
(Polling and webhook are mutually exclusive — the script deletes the webhook;
the next deploy re-registers it.)

## The demo beat

Send three messages about some made-up payer quirk → `/teach` → `/ask` the
question in the chat (or in the web UI) → cited answer sourced to the chat,
seconds later. That is the collection problem, closed live.
