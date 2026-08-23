"""Heading-aware chunking with contextual prefixes.

A chunk that says "limit is 2 per calendar year" is meaningless in isolation.
Prefixed with "Delta Dental CA Payer Playbook > Frequency limitations" it becomes
retrievable and quotable — the cheapest retrieval-quality win available. Both the
embedding text and the lexical index use the prefixed form.
"""
import re
from dataclasses import dataclass

from app import config

_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_CHARS_PER_TOKEN = 4  # good enough for sizing; we are not billing off this


@dataclass
class Chunk:
    ord: int
    heading: str
    text: str
    embed_text: str


def _sections(body: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, text) sections; text before any heading gets ''."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        m = _HEADING.match(line)
        if m:
            sections.append((m.group(2).strip(), []))
        else:
            sections[-1][1].append(line)
    return [(h, "\n".join(ls).strip()) for h, ls in sections if "\n".join(ls).strip()]


def chunk_document(title: str, body: str) -> list[Chunk]:
    target = config.CHUNK_TARGET_TOKENS * _CHARS_PER_TOKEN
    overlap = int(target * config.CHUNK_OVERLAP_RATIO)
    chunks: list[Chunk] = []

    for heading, text in _sections(body):
        start = 0
        while start < len(text):
            piece = text[start:start + target]
            # try to end on a paragraph or sentence boundary
            if start + target < len(text):
                cut = max(piece.rfind("\n\n"), piece.rfind(". "))
                if cut > target * 0.5:
                    piece = piece[:cut + 1]
            piece = piece.strip()
            if piece:
                prefix = f"{title} > {heading}" if heading else title
                chunks.append(Chunk(
                    ord=len(chunks),
                    heading=heading,
                    text=piece,
                    embed_text=f"{prefix}\n\n{piece}",
                ))
            if start + target >= len(text):
                break
            start += max(len(piece) - overlap, 1)

    if not chunks and body.strip():  # tiny doc, no headings
        chunks = [Chunk(0, "", body.strip(), f"{title}\n\n{body.strip()}")]
    return chunks
