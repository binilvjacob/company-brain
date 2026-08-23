"""Provision + deploy on Render via API. Runs in CI (deploy job).

Idempotent: finds-or-creates the Postgres instance and web service, syncs env
vars, triggers a deploy, waits for live, health-checks. Prints the public URL
as the last line so the workflow can capture it.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.render.com/v1"
KEY = os.environ["RENDER_API_KEY"]
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
REPO = os.environ.get("REPO_URL", "https://github.com/binilvjacob/company-brain")
REGION = os.environ.get("RENDER_REGION", "singapore")
DB_NAME = "company-brain-db"
SVC_NAME = "company-brain"


def api(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(
        f"{API}{path}", method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Accept": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            return json.loads(data) if data else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"!! {method} {path} -> {e.code}: {detail}", file=sys.stderr)
        raise


def owner_id() -> str:
    owners = api("GET", "/owners?limit=20")
    return owners[0]["owner"]["id"]


def find(kind: str, name: str):
    """kind: 'postgres' or 'services'. List responses wrap each item under a
    singular key: [{'postgres': {...}}] / [{'service': {...}}]."""
    wrapper = "postgres" if kind == "postgres" else "service"
    items = api("GET", f"/{kind}?name={name}&limit=20")
    for item in items:
        obj = item.get(wrapper)
        if obj and obj.get("name") == name:
            return obj
    return None


def ensure_postgres(oid: str) -> str:
    pg = find("postgres", DB_NAME)
    if not pg:
        print(f"creating postgres {DB_NAME} ...")
        pg = api("POST", "/postgres", {
            "name": DB_NAME, "ownerId": oid, "plan": "free",
            "region": REGION, "version": "16",
            "databaseName": "brain", "databaseUser": "brain",
        })
    pg_id = pg["id"]
    for _ in range(60):
        status = api("GET", f"/postgres/{pg_id}").get("status")
        print(f"  postgres status: {status}")
        if status == "available":
            break
        time.sleep(10)
    info = api("GET", f"/postgres/{pg_id}/connection-info")
    return info["internalConnectionString"]


def _unwrap(obj: dict, key: str) -> dict:
    """Render responses sometimes nest the resource under a singular key."""
    return obj.get(key, obj) if isinstance(obj, dict) else obj


def ensure_service(oid: str, database_url: str) -> tuple[dict, str | None]:
    """Returns (service, deploy_id_from_creation_or_None)."""
    svc = find("services", SVC_NAME)
    env_vars = [
        {"key": "DATABASE_URL", "value": database_url},
        {"key": "OPENAI_API_KEY", "value": OPENAI_KEY},
        {"key": "PYTHON_VERSION", "value": "3.11.9"},
        {"key": "CONFIDENCE_THRESHOLD", "value": os.environ.get("CONFIDENCE_THRESHOLD", "0.50")},
    ]
    if not svc:
        print(f"creating web service {SVC_NAME} ...")
        created = api("POST", "/services", {
            "type": "web_service", "name": SVC_NAME, "ownerId": oid,
            "repo": REPO, "branch": "main", "autoDeploy": "no",
            "envVars": env_vars,
            "serviceDetails": {
                "env": "python", "region": REGION, "plan": "free",
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "bash start.sh",
                },
            },
        })
        print(f"  create response keys: {sorted(created)}")
        return _unwrap(created, "service"), created.get("deployId")
    api("PUT", f"/services/{svc['id']}/env-vars", env_vars)
    return svc, None


def deploy_and_wait(svc_id: str, dep_id: str | None = None) -> None:
    if not dep_id:
        dep = api("POST", f"/services/{svc_id}/deploys", {})
        dep_id = _unwrap(dep, "deploy").get("id")
    if not dep_id:
        print(f"could not determine deploy id from response", file=sys.stderr)
        sys.exit(1)
    terminal = {"live", "build_failed", "update_failed", "canceled",
                "pre_deploy_failed", "deactivated"}
    status = ""
    for _ in range(120):
        status = _unwrap(api("GET", f"/services/{svc_id}/deploys/{dep_id}"),
                         "deploy").get("status")
        print(f"  deploy status: {status}")
        if status in terminal:
            break
        time.sleep(10)
    if status != "live":
        print(f"deploy ended in status {status}", file=sys.stderr)
        sys.exit(1)


def health_check(url: str) -> None:
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{url}/healthz", timeout=20) as resp:
                body = json.loads(resp.read())
                if body.get("ok"):
                    print(f"health: {body}")
                    return
        except Exception as e:  # noqa: BLE001 — free tier cold starts
            print(f"  waiting for health: {e}")
        time.sleep(10)
    print("service never became healthy", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    oid = owner_id()
    database_url = ensure_postgres(oid)
    svc, creation_deploy = ensure_service(oid, database_url)
    url = (svc.get("serviceDetails") or {}).get("url") or f"https://{SVC_NAME}.onrender.com"
    deploy_and_wait(svc["id"], creation_deploy)
    health_check(url)
    print(f"RENDER_URL={url}")


if __name__ == "__main__":
    main()
