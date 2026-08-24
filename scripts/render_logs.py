"""Tail the live service's logs via the Render API (diagnostic, best-effort).
Run from CI where RENDER_API_KEY lives. Prints whatever it can get."""
import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.render.com/v1"
KEY = os.environ.get("RENDER_API_KEY", "")
if not KEY:
    print("no RENDER_API_KEY; skipping")
    sys.exit(0)


def api(path):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {KEY}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"!! GET {path} -> {e.code}: {e.read()[:300]}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"!! GET {path} -> {e}")
        return None


services = api("/services?name=company-brain&limit=5") or []
svc = None
for item in services:
    obj = item.get("service") if isinstance(item, dict) else None
    if obj and obj.get("name") == "company-brain":
        svc = obj
        break
if not svc:
    print("service not found")
    sys.exit(0)

sid = svc["id"]
print(f"service {sid}  suspended={svc.get('suspended')}  updated={svc.get('updatedAt')}")

owner = svc.get("ownerId", "")
for qs in (f"/logs?ownerId={owner}&resource={sid}&limit=100",
           f"/logs?resource={sid}&limit=100",
           f"/logs?resourceIds={sid}&limit=100"):
    data = api(qs)
    if not data:
        continue
    logs = data.get("logs") if isinstance(data, dict) else data
    if not logs:
        print(f"(no logs via {qs})")
        continue
    print(f"--- logs via {qs} ({len(logs)} entries, oldest first) ---")
    for entry in logs[-100:]:
        msg = entry.get("message") if isinstance(entry, dict) else str(entry)
        ts = entry.get("timestamp", "") if isinstance(entry, dict) else ""
        print(f"{ts}  {str(msg)[:400]}")
    break

deploys = api(f"/services/{sid}/deploys?limit=3") or []
for d in deploys:
    dep = d.get("deploy", d) if isinstance(d, dict) else {}
    print("deploy", dep.get("id"), dep.get("status"),
          dep.get("createdAt"), "->", dep.get("finishedAt"))

events = api(f"/services/{sid}/events?limit=15") or []
for ev in events:
    e = ev.get("event", ev) if isinstance(ev, dict) else {}
    print("event", e.get("timestamp"), e.get("type"),
          str(e.get("details"))[:200])
