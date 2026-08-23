"""SourceAdapter: the seam where real connectors plug in.

We deliberately did NOT build live OAuth connectors for a 3-day prototype — that
is a day of plumbing a reviewer can't see. Instead every source funnels through
this interface into one canonical KnowledgeObject. Adding a real Notion/Slack/
Drive connector later is a ~50-line file that implements `load()`; see
notion_stub.py for the typed template.
"""
from pathlib import Path
from typing import Iterable, Protocol

from app.models import KnowledgeObject


class SourceAdapter(Protocol):
    def load(self, root: Path) -> Iterable[KnowledgeObject]:
        """Yield canonical KnowledgeObjects from this source."""
        ...


def load_corpus(corpus_dir: Path) -> list[KnowledgeObject]:
    """Run every adapter over the corpus directory."""
    from app.adapters.csv_adapter import CSVAdapter
    from app.adapters.markdown import MarkdownAdapter
    from app.adapters.slack_export import SlackExportAdapter

    objects: list[KnowledgeObject] = []
    for adapter in (MarkdownAdapter(), CSVAdapter(), SlackExportAdapter()):
        objects.extend(adapter.load(corpus_dir))
    return objects
