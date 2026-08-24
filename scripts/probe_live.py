"""Latency probe for the live deploy — including a PROPERLY SIGNED slash
command, which is the one path plain smoke can't exercise. Run from CI
(workflow_dispatch on the `probe` branch) where the signing secret lives.
Prints timings; exits 0 always — this is a diagnostic, not a gate."""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

URL = (sys.argv[1] if len(sys.argv) > 1
       else Path("deploy/render_url.txt").read_text().strip())
SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")


def timed(name, method, path, data=None, headers=None, timeout=25):
    t0 = time.monotonic()
    req = urllib.request.Request(f"{URL}{path}", data=data,
                                 headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()[:300]
            print(f"{time.monotonic()-t0:7.2f}s  {r.status}  {name}  {body[:160]!r}")
    except urllib.error.HTTPError as e:
        print(f"{time.monotonic()-t0:7.2f}s  {e.code}  {name}  {e.read()[:160]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{time.monotonic()-t0:7.2f}s  ERR  {name}  {e}")


def signed_slash(name, form: dict):
    raw = urllib.parse.urlencode(form).encode()
    ts = str(int(time.time()))
    sig = "v0=" + hmac.new(SECRET.encode(), f"v0:{ts}:".encode() + raw,
                           hashlib.sha256).hexdigest()
    timed(name, "POST", "/hooks/slack/commands", data=raw, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sig,
    })


print(f"probe against {URL}  (signing secret: {'SET' if SECRET else 'MISSING'})")

timed("healthz #1", "GET", "/healthz")
timed("healthz #2", "GET", "/healthz")
timed("events: url_verification", "POST", "/hooks/slack",
      data=json.dumps({"type": "url_verification", "challenge": "probe"}).encode(),
      headers={"Content-Type": "application/json"})
timed("commands: unsigned (expect 403)", "POST", "/hooks/slack/commands",
      data=b"command=/ask&text=x",
      headers={"Content-Type": "application/x-www-form-urlencoded"})

base = {"channel_id": "CPROBE01", "channel_name": "probe",
        "user_name": "probe", "response_url": "https://example.com/void"}
if SECRET:
    signed_slash("commands: SIGNED /team bogus (upsert_chat path, expect ack)",
                 {**base, "command": "/team", "text": "bogusteam"})
    signed_slash("commands: SIGNED /ask #1 (expect 200 ack fast)",
                 {**base, "command": "/ask",
                  "text": "What is the D4910 frequency rule for Delta Dental of California?"})
    signed_slash("commands: SIGNED /ask #2 (repeat)",
                 {**base, "command": "/ask",
                  "text": "What is the D4910 frequency rule for Delta Dental of California?"})

timed("web /ask (full LLM control)", "POST", "/ask",
      data=json.dumps({"q": "What is the D4910 frequency rule for Delta Dental "
                            "of California?"}).encode(),
      headers={"Content-Type": "application/json"}, timeout=60)
timed("healthz #3 (after)", "GET", "/healthz")
print("probe done")
