"""Markdown adapter: .md files with YAML frontmatter → KnowledgeObject."""
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml

from app.models import KnowledgeObject


class MarkdownAdapter:
    def load(self, root: Path) -> Iterable[KnowledgeObject]:
        for path in sorted(root.rglob("*.md")):
            if path.name in ("README.md",):
                continue
            raw = path.read_text(encoding="utf-8")
            meta, body = self._split_frontmatter(raw)
            if meta is None:
                continue  # not a corpus doc
            updated = meta.get("updated_at")
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated)
            elif isinstance(updated, date) and not isinstance(updated, datetime):
                updated = datetime(updated.year, updated.month, updated.day)
            if isinstance(updated, datetime) and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            yield KnowledgeObject(
                id=meta.get("id", path.stem),
                title=meta["title"],
                body=body.strip(),
                source_type="markdown",
                source_url=meta.get("source_url", f"corpus/{path.relative_to(root)}"),
                team=meta["team"],
                doc_type=meta["doc_type"],
                owner=meta["owner"],
                updated_at=updated,
                visibility=list(meta.get("visibility", ["everyone"])),
                entities=[str(e) for e in meta.get("entities", [])],
            )

    @staticmethod
    def _split_frontmatter(raw: str):
        if not raw.startswith("---"):
            return None, raw
        parts = raw.split("---", 2)
        if len(parts) < 3:
            return None, raw
        return yaml.safe_load(parts[1]), parts[2]
