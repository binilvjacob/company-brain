"""Notion adapter — typed stub.

This is the shape of the 50-line file that turns a mock corpus into a live one.
It is deliberately not implemented: live OAuth plumbing is invisible in a demo
and costs a day. The interface contract is the deliverable.

To make it real:
  1. pip install notion-client; NOTION_TOKEN in env (integration token).
  2. `load()` walks the shared pages via client.search / blocks.children.list,
     renders blocks to markdown, maps page properties → team/doc_type/owner,
     uses last_edited_time as updated_at.
  3. Everything downstream (redaction, chunking, ranking, citations) is already
     source-agnostic — no other file changes.
"""
from pathlib import Path
from typing import Iterable

from app.models import KnowledgeObject


class NotionAdapter:
    def __init__(self, token: str | None = None, root_page_id: str | None = None):
        self.token = token
        self.root_page_id = root_page_id

    def load(self, root: Path) -> Iterable[KnowledgeObject]:
        raise NotImplementedError(
            "Live Notion sync is intentionally out of scope for the prototype; "
            "see module docstring for the 50-line implementation plan."
        )
