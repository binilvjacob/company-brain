"""Central configuration. Everything tunable lives here, driven by env vars."""
import os


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


DATABASE_URL = env("DATABASE_URL", "postgresql://brain:brain@127.0.0.1:5432/brain")

# Providers: "openai" for real calls, "mock" for deterministic offline behaviour
# (tests, local dev without a key). The mock embedder is a hashed bag-of-words,
# so lexical overlap still produces usable similarity in tests.
EMBEDDINGS_PROVIDER = env("EMBEDDINGS_PROVIDER", "openai" if env("OPENAI_API_KEY") else "mock")
LLM_PROVIDER = env("LLM_PROVIDER", "openai" if env("OPENAI_API_KEY") else "mock")

OPENAI_API_KEY = env("OPENAI_API_KEY")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536
GENERATION_MODEL = env("GENERATION_MODEL", "gpt-4o-mini")

# Retrieval knobs (values re-validated by `make eval`; see WRITEUP.md).
CANDIDATES_PER_ARM = int(env("CANDIDATES_PER_ARM", "40"))
TOP_K = int(env("TOP_K", "10"))
RRF_K = int(env("RRF_K", "60"))
# Metadata boosts are MULTIPLICATIVE fractions on the fused relevance score:
#   score = rrf * (1 + W_FRESHNESS*freshness + W_AUTHORITY*authority + W_TEAM*match)
# RRF's dynamic range is tiny (1/61 .. 1/100 per arm); additive boosts at any
# useful size would overwhelm relevance entirely (found the hard way in eval —
# see WRITEUP failure notes). Multiplicative boosts break near-ties without
# letting a fresh-but-irrelevant doc outrank a genuinely relevant one.
W_FRESHNESS = float(env("W_FRESHNESS", "0.25"))
W_AUTHORITY = float(env("W_AUTHORITY", "0.15"))
W_TEAM_MATCH = float(env("W_TEAM_MATCH", "0.10"))
FRESHNESS_HALF_LIFE_DAYS = float(env("FRESHNESS_HALF_LIFE_DAYS", "180"))

# Confidence gate: below this the Brain refuses and logs a gap instead of
# guessing. 0.50 is the measured operating point from the eval threshold sweep
# (real embeddings): lowest answerable-question confidence 0.594, so 0.50
# gates 5/6 unanswerables while wrongly refusing none. Calibrated on 31
# questions — treat as a starting point, not proof.
CONFIDENCE_THRESHOLD = float(env("CONFIDENCE_THRESHOLD", "0.50"))
STALENESS_WARN_DAYS = int(env("STALENESS_WARN_DAYS", "120"))

CHUNK_TARGET_TOKENS = int(env("CHUNK_TARGET_TOKENS", "800"))
CHUNK_OVERLAP_RATIO = float(env("CHUNK_OVERLAP_RATIO", "0.15"))

# Live connectors (v1: Telegram — app/connectors/telegram.py). The bot token
# enables the connector; CONNECTOR_SECRET authenticates both the inbound
# webhook (Telegram echoes it in a header) and POST /sync/run.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
CONNECTOR_SECRET = env("CONNECTOR_SECRET")
TELEGRAM_DEFAULT_TEAM = env("TELEGRAM_DEFAULT_TEAM", "ops")
DIGEST_QUIET_MINUTES = int(env("DIGEST_QUIET_MINUTES", "30"))
DIGEST_MIN_MESSAGES = int(env("DIGEST_MIN_MESSAGES", "3"))

# Slack (v1.2 — app/connectors/slack.py). A single-workspace install issues
# the bot token from the app dashboard: token-based like Telegram, no OAuth
# flow. The signing secret authenticates every inbound Slack request (HMAC).
SLACK_BOT_TOKEN = env("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = env("SLACK_SIGNING_SECRET")
SLACK_DEFAULT_TEAM = env("SLACK_DEFAULT_TEAM", "ops")

# Self-ping (free-tier honesty, part 2): Render idles a free instance after a
# few quiet minutes, and a slash command that lands on a sleeping instance is
# void — Slack allows 3 seconds, the wake takes ~40. An external cron can't be
# trusted to be punctual (GitHub's fired at 30-68 min gaps on a 10-min
# schedule), so the app requests itself through its public URL, which counts
# as inbound traffic at the platform edge. 0 disables.
SELF_PING_SECONDS = int(env("SELF_PING_SECONDS", "240"))

# Authority: an SOP should outrank a Slack message at equal relevance.
DOC_TYPE_AUTHORITY = {
    "sop": 1.0,
    "playbook": 0.95,
    "policy": 0.9,
    "prd": 0.9,
    "runbook": 0.9,
    "spec": 0.9,
    "resolution": 0.85,
    "case_study": 0.85,
    "glossary": 0.8,
    "notes": 0.7,
    "slack_thread": 0.6,
    "chat_thread": 0.6,   # ambient Telegram/WhatsApp digests — same trust tier as Slack
}

TEAMS = ["ops", "product", "eng", "gtm", "ga", "meta"]
ROLES = ["everyone", "ops", "leadership"]

# Gap routing: which human owns unanswered questions for a team.
TEAM_OWNER = {
    "ops": "priya",
    "product": "lena",
    "eng": "nakul",
    "gtm": "chris",
    "ga": "maya",
    "meta": "priya",
}

# USD per 1M tokens (prices as listed 2026-08; used for the cost-per-query metric).
PRICES = {
    "text-embedding-3-small": {"in": 0.02, "out": 0.0},
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
}

ACRONYMS = {
    "ARC": "Accelerated Revenue Cycle",
    "STR": "straight-through rate",
    "PMS": "practice management system",
    "COB": "coordination of benefits",
    "SRP": "scaling and root planing",
    "EOB": "explanation of benefits",
    "FMX": "full mouth x-rays",
    "AHT": "average handle time",
    "DSO": "dental support organization",
    "RCM": "revenue cycle management",
    "HITL": "human in the loop",
    "MTC": "missing tooth clause",
    "DDCA": "Delta Dental of California",
    "FEP": "Federal Employee Program BlueDental",
    "UHC": "UnitedHealthcare",
}
