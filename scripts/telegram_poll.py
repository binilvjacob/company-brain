"""Local dev for the Telegram connector — no public URL needed.

Deletes any registered webhook, then long-polls getUpdates and feeds each
update through the exact same handler the webhook uses. Ctrl-C to stop.

  TELEGRAM_BOT_TOKEN=... DATABASE_URL=... python scripts/telegram_poll.py
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import config, db  # noqa: E402
from app.connectors import telegram as tg  # noqa: E402


def api(method: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


def main() -> int:
    if not tg.enabled():
        print("TELEGRAM_BOT_TOKEN is not set")
        return 1
    conn = db.connect()
    db.init_schema(conn)
    print("deleting webhook (polling and webhook are mutually exclusive):",
          api("deleteWebhook", {}))
    offset = 0
    print("polling — send the bot a message, or /help")
    while True:
        resp = api("getUpdates", {"timeout": 50, "offset": offset,
                                  "allowed_updates": ["message"]})
        for update in resp.get("result", []):
            offset = update["update_id"] + 1
            preview = (update.get("message") or {}).get("text", "")[:60]
            print(f"  update {update['update_id']}: {preview}")
            tg.handle_update(conn, update)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
