"""Eval harness. `make eval` reproduces the table in the README.

Metrics, reported honestly:
- Recall@5      — an expected source doc appears in the top-5 retrieved docs
- Answer rate   — answerable questions that got an answer (vs wrong refusal)
- Groundedness  — every claim in the answer supported by its cited chunks
                  (LLM-judged in real mode; citation-presence check in mock)
- Refusal acc.  — unanswerable questions correctly refused (not hallucinated)
- p50 latency, mean cost/query

Also prints a confidence-threshold sweep (no extra LLM calls) so the operating
point of the refusal gate is chosen from data, not vibes.
"""
import json
import statistics
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import config, db  # noqa: E402
from app.answer import ask  # noqa: E402
from app.llm import generate_json  # noqa: E402
from app.retrieval import confidence, search  # noqa: E402

ROOT = Path(__file__).parent
JUDGE_PROMPT = """You are grading a RAG answer for groundedness.
Question: {q}
Answer: {answer}
Cited source chunks:
{chunks}
Is EVERY factual claim in the answer supported by the cited chunks? Minor
rephrasing is fine; any unsupported number, rule, or entity is a fail.
Return JSON: {{"grounded": bool, "unsupported_claim": str|null}}"""


def run() -> dict:
    questions = yaml.safe_load((ROOT / "questions.yaml").read_text())
    conn = db.connect()
    rows, latencies, costs, confidences = [], [], [], []

    for item in questions:
        t0 = time.perf_counter()
        results = search(conn, item["q"], role=item.get("role", "everyone"))
        docs_top5 = list(dict.fromkeys(r.doc_id for r in results))[:5]
        conf = confidence(results)
        out = ask(conn, item["q"], role=item.get("role", "everyone"))
        latency = (time.perf_counter() - t0) * 1000

        row = {
            "id": item["id"], "answerable": item["answerable"],
            "confidence": round(conf, 3), "answered": out["answered"],
            "latency_ms": int(latency), "cost_usd": out.get("cost_usd", 0.0),
        }
        confidences.append((conf, item["answerable"]))
        latencies.append(latency)
        costs.append(out.get("cost_usd", 0.0))

        if item["answerable"]:
            expected = set(item.get("expected_docs", []))
            row["recall_at_5"] = bool(expected & set(docs_top5)) if expected else None
            row["retrieved_top5"] = docs_top5
            if out["answered"]:
                text = out["answer_markdown"]
                expect_any = item.get("expect_any", [])
                row["expect_hit"] = (any(e.lower() in text.lower() for e in expect_any)
                                     if expect_any else None)
                if config.LLM_PROVIDER == "openai":
                    chunks = "\n\n".join(
                        f"[{c['n']}] {c['title']} > {c['heading']}" for c in out["citations"])
                    full_chunks = "\n\n".join(
                        f"[{c['n']}] " + conn.execute(
                            "SELECT text FROM chunks WHERE id = %s",
                            (c["chunk_id"],)).fetchone()["text"]
                        for c in out["citations"])
                    judge = generate_json(
                        "You grade answers strictly. JSON only.",
                        JUDGE_PROMPT.format(q=item["q"], answer=text, chunks=full_chunks))
                    row["grounded"] = bool(judge.get("grounded"))
                    row["unsupported_claim"] = judge.get("unsupported_claim")
                else:
                    row["grounded"] = bool(out["citations"])
        rows.append(row)

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    recalls = [r["recall_at_5"] for r in answerable if r.get("recall_at_5") is not None]
    grounded = [r["grounded"] for r in answerable if "grounded" in r]

    summary = {
        "provider": {"embeddings": config.EMBEDDINGS_PROVIDER, "llm": config.LLM_PROVIDER,
                     "threshold": config.CONFIDENCE_THRESHOLD},
        "n_questions": len(rows),
        "recall_at_5": round(sum(recalls) / len(recalls), 3) if recalls else None,
        "answer_rate": round(sum(r["answered"] for r in answerable) / len(answerable), 3),
        "groundedness": round(sum(grounded) / len(grounded), 3) if grounded else None,
        "refusal_accuracy": round(
            sum(not r["answered"] for r in unanswerable) / len(unanswerable), 3),
        "p50_latency_ms": int(statistics.median(latencies)),
        "mean_cost_usd": round(statistics.mean(costs), 5),
    }

    # Threshold sweep on recorded confidences — pick the gate from data.
    sweep = {}
    for th in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        wrong_refusals = sum(1 for c, ans in confidences if ans and c < th)
        caught = sum(1 for c, ans in confidences if not ans and c < th)
        sweep[th] = {"answerable_refused": wrong_refusals,
                     "unanswerable_gated": f"{caught}/{len(unanswerable)}"}

    report = {"summary": summary, "threshold_sweep": sweep, "rows": rows}
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(report, indent=2))

    md = ["| Metric | Value |", "|---|---|"]
    labels = {"recall_at_5": "Recall@5", "answer_rate": "Answer rate (answerable)",
              "groundedness": "Groundedness", "refusal_accuracy": "Refusal accuracy",
              "p50_latency_ms": "p50 latency (ms)", "mean_cost_usd": "Mean cost/query (USD)"}
    for k, label in labels.items():
        md.append(f"| {label} | {summary[k]} |")
    md_text = "\n".join(md)
    (out_dir / "results.md").write_text(md_text + "\n")

    print(json.dumps(summary, indent=2))
    print("\nThreshold sweep (gate too low → hallucination risk; too high → refuses good questions):")
    for th, s in sweep.items():
        print(f"  {th:.2f}: wrongly-refused answerable={s['answerable_refused']:2d}  "
              f"unanswerable gated={s['unanswerable_gated']}")
    failures = [r["id"] for r in answerable if r.get("recall_at_5") is False]
    wrong_ref = [r["id"] for r in answerable if not r["answered"]]
    halluc = [r["id"] for r in unanswerable if r["answered"]]
    if failures:
        print(f"\nRecall misses: {failures}")
    if wrong_ref:
        print(f"Wrongly refused: {wrong_ref}")
    if halluc:
        print(f"Answered but should refuse: {halluc}")
    return report


if __name__ == "__main__":
    run()
