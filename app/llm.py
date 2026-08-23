"""Thin generation wrapper. One function, JSON in/out, swappable provider.

The mock provider is context-faithful enough to exercise the whole /ask contract
in tests: it cites when context exists and declines when it does not — which is
exactly the behaviour the real prompt demands of the real model.
"""
import json

from app import config

_usage = {"in": 0, "out": 0}


def llm_usage() -> dict:
    return dict(_usage)


def generation_cost_usd() -> float:
    p = config.PRICES.get(config.GENERATION_MODEL, {"in": 0, "out": 0})
    return (_usage["in"] * p["in"] + _usage["out"] * p["out"]) / 1_000_000


def _mock_generate(system: str, user: str) -> str:
    """Deterministic stand-in: if numbered context blocks are present, produce an
    answer citing them; otherwise refuse. Mirrors the contract the real prompt
    enforces, so the whole /ask and recipe pipeline is testable offline."""
    import re
    blocks = sorted({int(m) for m in re.findall(r"^\[(\d+)\]", user, re.M)})
    if blocks:
        first = user.split(f"[{blocks[0]}]", 1)[1][:400].strip().replace("\n", " ")
        cited = blocks[:6]
        return json.dumps({
            "can_answer": True,
            "answer_markdown": f"{first[:220]} " + "".join(f"[{n}]" for n in cited),
            "citations": cited,
            "staleness_note": None,
        })
    return json.dumps({"can_answer": False, "answer_markdown": "",
                       "citations": [], "reason": "no relevant context"})


def generate_json(system: str, user: str) -> dict:
    if config.LLM_PROVIDER == "mock":
        raw = _mock_generate(system, user)
    else:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.GENERATION_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        _usage["in"] += resp.usage.prompt_tokens
        _usage["out"] += resp.usage.completion_tokens
        raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"can_answer": False, "answer_markdown": "", "citations": [],
                "reason": "model returned unparseable output"}
