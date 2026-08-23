"""Slack export adapter: standard export JSON → one KnowledgeObject per thread.

Slack is where SOPs get corrected before anyone updates the SOP. Threads carry
low authority in ranking (a Slack message is not an SOP) but high freshness —
which is exactly how a 3-week-old correction outranks an 8-month-old SOP.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.models import KnowledgeObject


class SlackExportAdapter:
    def load(self, root: Path) -> Iterable[KnowledgeObject]:
        path = root / "meta" / "slack-export.json"
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for channel in data.get("channels", []):
            for thread in channel.get("threads", []):
                lines = [
                    f"{m['user']} ({datetime.fromtimestamp(float(m['ts']), tz=timezone.utc):%Y-%m-%d %H:%M}): {m['text']}"
                    for m in thread["messages"]
                ]
                last_ts = max(float(m["ts"]) for m in thread["messages"])
                first = thread["messages"][0]
                yield KnowledgeObject(
                    id=f"slack-{channel['name']}-{thread['thread_id']}",
                    title=f"#{channel['name']}: {thread.get('topic') or first['text'][:80]}",
                    body="\n\n".join(lines),
                    source_type="slack_export",
                    source_url=f"slack://{channel['name']}/{thread['thread_id']}",
                    team=channel.get("team", "meta"),
                    doc_type="slack_thread",
                    owner=first["user"],
                    updated_at=datetime.fromtimestamp(last_ts, tz=timezone.utc),
                    entities=thread.get("entities", []),
                )
