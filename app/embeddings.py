"""Embedding provider behind one function. OpenAI in prod, deterministic mock for
tests/offline dev (hashed bag-of-words — lexical overlap still yields similarity,
so retrieval logic is testable without a key)."""
import hashlib
import math
import re

from app import config

_usage = {"tokens": 0}

_STOP = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "is", "are",
    "was", "were", "what", "which", "how", "does", "do", "with", "at", "by",
    "from", "it", "this", "that", "we", "our", "as", "be", "per", "not", "no",
}


def embedding_usage() -> dict:
    return dict(_usage)


def _mock_embed(texts: list[str]) -> list[list[float]]:
    out = []
    for text in texts:
        vec = [0.0] * config.EMBEDDING_DIM
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            if tok in _STOP:
                continue
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % config.EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        out.append([v / norm for v in vec])
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if config.EMBEDDINGS_PROVIDER == "mock":
        return _mock_embed(texts)

    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):
        batch = [t[:8000] for t in texts[i:i + 100]]
        resp = client.embeddings.create(model=config.EMBEDDING_MODEL, input=batch)
        _usage["tokens"] += resp.usage.total_tokens
        out.extend(d.embedding for d in resp.data)
    return out


def embed_one(text: str) -> list[float]:
    return embed_texts([text])[0]
