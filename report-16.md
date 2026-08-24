# CI report — run 16 (52580cdac4a3e573c1129139744ecc10402dfd51)

| job | result |
|---|---|
| test | success |
| eval | success |
| deploy | success |
| smoke | success |

## Eval results
| Metric | Value |
|---|---|
| Recall@5 | 1.0 |
| Answer rate (answerable) | 1.0 |
| Groundedness | 1.0 |
| Refusal accuracy | 1.0 |
| p50 latency (ms) | 2035 |
| Mean cost/query (USD) | 0.00028 |

## Eval output tail
```
{
  "provider": {
    "embeddings": "openai",
    "llm": "openai",
    "threshold": 0.5
  },
  "n_questions": 31,
  "recall_at_5": 1.0,
  "answer_rate": 1.0,
  "groundedness": 1.0,
  "refusal_accuracy": 1.0,
  "p50_latency_ms": 2035,
  "mean_cost_usd": 0.00028
}

Threshold sweep (gate too low → hallucination risk; too high → refuses good questions):
  0.20: wrongly-refused answerable= 0  unanswerable gated=0/6
  0.25: wrongly-refused answerable= 0  unanswerable gated=0/6
  0.30: wrongly-refused answerable= 0  unanswerable gated=0/6
  0.35: wrongly-refused answerable= 0  unanswerable gated=1/6
  0.40: wrongly-refused answerable= 0  unanswerable gated=3/6
  0.45: wrongly-refused answerable= 0  unanswerable gated=4/6
  0.50: wrongly-refused answerable= 0  unanswerable gated=5/6
```

## Seed output tail
```
seed: 114 documents, 344 chunks, 9 redactions, 3 recipes
```

## Live smoke
```
PASS  healthz  (docs=115)
PASS  page /
PASS  page /recipes-ui
PASS  page /gaps-ui
PASS  page /sources
PASS  page /docs
PASS  page /r/triage-assist
PASS  page /sources/payer-playbook-ddca
PASS  ask: DDCA contradiction answered with citations  (conf=0.89)
PASS  ask: DDCA answer reflects the post-May-2026 rule  (delta dental of california (ddca) no longer counts perio maintenance (d4910) against the c)
PASS  ask: Humana refused (not hallucinated)  (conf=0.473)
PASS  ask: comp bands do not leak at role=everyone
PASS  triage: answered with citations
PASS  triage: past resolutions surfaced  (['playbook', 'resolution'])
PASS  gaps: Humana refusal logged
PASS  telegram: webhook auth enforced  (status=403)
PASS  slack: url_verification echoes (manifest liveness)
PASS  slack: events auth enforced  (status=403)
PASS  slack: commands auth enforced  (status=403)
PASS  slack: commands ack under 3s  (0.85s)

All live smoke checks passed.
```

## Deploy
RENDER_URL=https://company-brain-cugn.onrender.com

```
  postgres status: available
  deploy status: build_in_progress
  deploy status: build_in_progress
  deploy status: build_in_progress
  deploy status: update_in_progress
  deploy status: update_in_progress
  deploy status: update_in_progress
  deploy status: live
health: {'ok': True, 'connectors': {'telegram': True, 'slack': True}, 'docs': 115, 'chunks': 346}
RENDER_URL=https://company-brain-cugn.onrender.com
```

## Test output tail
```
............................                                             [100%]
=============================== warnings summary ===============================
app/api.py:103
  /home/runner/work/company-brain/company-brain/app/api.py:103: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

../../../../../opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/fastapi/applications.py:4681
  /opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/fastapi/applications.py:4681: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
28 passed, 2 warnings in 1.41s
```
