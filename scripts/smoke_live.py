"""Live-site smoke test: every demo path, against the deployed URL.

Run by CI after deploy. Asserts the paths a reviewer will actually click:
cited answer on the planted contradiction, honest refusal on the missing
payer, triage recipe returning past resolutions, and every UI page serving.
"""
import json
import sys
import urllib.request
from pathlib import Path

URL = (sys.argv[1] if len(sys.argv) > 1
       else Path("deploy/render_url.txt").read_text().strip())
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILURES.append(name)


def get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(f"{URL}{path}", timeout=90) as r:
            return r.status, r.read().decode()
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{URL}{path}", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


status, body = get("/healthz")
health = json.loads(body) if status == 200 else {}
check("healthz", status == 200 and health.get("ok") and health.get("docs", 0) >= 100,
      f"docs={health.get('docs')}")

for page in ("/", "/recipes-ui", "/gaps-ui", "/sources", "/docs",
             "/r/triage-assist", "/sources/payer-playbook-ddca"):
    s, _ = get(page)
    check(f"page {page}", s == 200)

ddca = post("/ask", {"q": "Does Delta Dental of California count perio maintenance "
                          "(D4910) against the cleaning frequency limit?"})
check("ask: DDCA contradiction answered with citations",
      ddca.get("answered") is True and len(ddca.get("citations", [])) > 0,
      f"conf={ddca.get('confidence')}")
text = ddca.get("answer_markdown", "").lower()
check("ask: DDCA answer reflects the post-May-2026 rule",
      any(k in text for k in ("no longer", "4 per", "unpooled", "may 2026", "2026-05",
                              "separate")), text[:90])

humana = post("/ask", {"q": "What are Humana's eligibility verification quirks?"})
check("ask: Humana refused (not hallucinated)", humana.get("answered") is False,
      f"conf={humana.get('confidence')}")

comp = post("/ask", {"q": "What is the compensation band for an L3 engineer in India?",
                     "role": "everyone"})
check("ask: comp bands do not leak at role=everyone",
      comp.get("answered") is False or
      all("comp" not in c["doc_id"] for c in comp.get("citations", [])))

triage = post("/recipes/triage-assist/run", {"inputs": {
    "payer": "Delta Dental of California", "procedure": "D4910",
    "flag_reason": "frequency history conflict",
    "portal_output": "history shows 2 hygiene visits YTD"}})
check("triage: answered with citations", triage.get("answered") is True
      and len(triage.get("citations", [])) > 0)
check("triage: past resolutions surfaced",
      any(c["doc_type"] == "resolution" for c in triage.get("citations", [])),
      str(sorted({c['doc_type'] for c in triage.get('citations', [])})))

gaps = get("/gaps")[1]
check("gaps: Humana refusal logged", "humana" in gaps.lower())

if FAILURES:
    print(f"\n{len(FAILURES)} smoke failure(s): {FAILURES}")
    sys.exit(1)
print("\nAll live smoke checks passed.")
