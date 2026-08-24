# Slack connector — 5-minute setup

The Brain's second **live** source, and the receipt for a claim the writeup
made at v1: Slack's Events API is the same webhook shape as Telegram's, so
each new chat connector is *scope, not design*. The transport differs (HMAC
request signing, a one-time URL challenge, a 3-second slash-command ack
budget); the buffer → quiet-window digest → vouched capture core is shared
(`app/connectors/common.py`).

A free Slack workspace is enough — app creation, bot tokens, the Events API,
and slash commands are not gated by plan.

## 1. Create the app (2 minutes, at api.slack.com/apps)

1. **Create New App** → **From a manifest** → pick your workspace → paste
   [docs/slack-manifest.yml](slack-manifest.yml) (URLs already point at the
   live deploy; change them if you run your own).
2. **Install to Workspace** (this is a dashboard button, not an OAuth flow —
   a single-workspace install issues the token directly, same trust posture
   as a BotFather token).
3. Copy two values: **Bot User OAuth Token** (`xoxb-…`, under *OAuth &
   Permissions*) and the **Signing Secret** (under *Basic Information*).

## 2. Configure the deployment (2 minutes, in GitHub)

Repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Value |
|---|---|
| `SLACK_BOT_TOKEN` | the `xoxb-…` token |
| `SLACK_SIGNING_SECRET` | the signing secret |

Then run the pipeline once (push anything, or Actions → *pipeline* → *Run
workflow*). The deploy job syncs the secrets into Render. `GET /healthz`
shows `"connectors": {"slack": true}` when it's live. There is no webhook
registration step at all: the manifest pinned the request URL, and the
endpoint answers Slack's URL check even while the connector is dark — which
is why the manifest applies cleanly before the secrets exist.

## 3. Use it

Invite the bot to a channel (`/invite @Company Brain`) and:

- **just talk** — every message is buffered (Slack markup normalized, then
  identifiers PHI-redacted *before* storage); once the channel is quiet for
  30 minutes, the run is distilled into one low-authority `slack_thread`
  knowledge object — the same shelf and trust tier as the v1 Slack-export
  adapter's threads. The adapter proved the shape on files; this removes the
  files. (The keepwarm cron flushes quiet channels every 10 minutes via
  `POST /sync/run`.)
- **`@Company Brain <question>`** — a cited answer in the thread, or an
  honest refusal that lands in the Gaps dashboard, routed to an owner.
- **`/ask <question>`** — same, as a slash command. It acks instantly
  ("Asking the Brain…") and delivers through the command's `response_url`:
  Slack voids commands unanswered in 3 seconds, and answering alone has a
  ~2s p50.
- **`/teach`** — capture the last 20 messages (or `/teach 5`) right now as a
  higher-authority `notes` object with provenance: who taught, which
  channel, which messages. Vouched beats ambient.
- **`/team gtm`** — file this channel's knowledge under a different team
  (default `ops`).

## Why live-first is the only honest Slack design

Since May 2025, Slack rate-limits `conversations.history` and
`conversations.replies` for new non-Marketplace apps to **1 request/minute,
15 messages per call**. Export-then-index RAG is dead on arrival for a new
app; knowledge has to be captured as it is said. This connector never calls
the history API at all — what it missed while dark stays missed, by design.
The architecture the Brain already had for Telegram (live events, boundary
redaction, distill-on-quiet) is the one Slack's own platform rules now force.

## The demo beat

Say three messages about some made-up payer quirk → `/teach` → `/ask` the
question in the channel (or in the web UI) → cited answer sourced to the
channel, seconds later — and the same `/ask` in the web UI can cite Telegram
and Slack knowledge side by side. One brain, many mouths.
