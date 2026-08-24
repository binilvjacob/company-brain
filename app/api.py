"""Brain API + UI. FastAPI's /docs page doubles as the platform demo surface."""
import json
import os
import secrets as pysecrets
import traceback
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app import config, db
from app.answer import ask
from app.capture import list_gaps, teach
from app.connectors import common as connector_common
from app.connectors import slack as sl
from app.connectors import telegram as tg
from app.ingest import ingest_document
from app.models import KnowledgeObject
from app.recipes import get_recipe, list_recipes, run_recipe, save_recipe
from app.retrieval import search

app = FastAPI(
    title="Needletail Company Brain",
    description=(
        "One place where company knowledge lives, can be queried to get work done, "
        "and lets any team member build small tools on top of it. "
        "Cited answers or honest refusals — nothing in between."
    ),
    version="0.1.0",
)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "ui" / "templates"))


def _conn():
    if not hasattr(app.state, "conn") or app.state.conn.closed:
        app.state.conn = db.connect()
    return app.state.conn


# --------------------------------------------------------------------------- API

class SearchBody(BaseModel):
    q: str
    role: str = "everyone"
    teams: list[str] | None = None
    top_k: int | None = None


class AskBody(BaseModel):
    q: str
    role: str = "everyone"
    teams: list[str] | None = None


class IngestBody(BaseModel):
    id: str
    title: str
    body: str
    team: str
    doc_type: str
    owner: str
    source_type: str = "api"
    source_url: str = ""
    visibility: list[str] = ["everyone"]
    entities: list[str] = []
    provenance: dict | None = None


class RecipeRunBody(BaseModel):
    inputs: dict = {}
    role: str = "everyone"


class RecipeCreateBody(BaseModel):
    name: str
    description: str = ""
    inputs: list[dict] = []
    retrieval: dict
    prompt: str
    created_by: str = "api"


@app.on_event("startup")
def _wire_connectors():
    # On Render, RENDER_EXTERNAL_URL is set by the platform — a deploy with the
    # bot token configured registers its own webhook. Zero manual wiring.
    # (Slack needs no registration call: its app manifest pins the request URL,
    # and the endpoint answers the manifest's liveness challenge even dark.)
    base = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if tg.enabled() and base:
        tg.register_webhook(base)


@app.get("/healthz")
def healthz():
    return {"ok": True,
            "connectors": {"telegram": tg.enabled(), "slack": sl.enabled()},
            **db.counts(_conn())}


# --------------------------------------------------------------- connectors

def _secret_ok(given: str) -> bool:
    return bool(config.CONNECTOR_SECRET) and \
        pysecrets.compare_digest(given or "", config.CONNECTOR_SECRET)


@app.post("/hooks/telegram")
async def telegram_hook(request: Request):
    """Inbound updates from Telegram. Auth: Telegram echoes the secret_token we
    set at webhook registration in a header — anything else is rejected."""
    if not tg.enabled():
        return JSONResponse({"ok": False, "detail": "connector not configured"},
                            status_code=503)
    if not _secret_ok(request.headers.get("x-telegram-bot-api-secret-token", "")):
        return JSONResponse({"ok": False}, status_code=403)
    update = await request.json()
    try:
        # Threadpool, never the event loop: handling can include LLM calls
        # (ambient digest, /ask). Sync work on the loop would freeze every
        # async endpoint — Slack's 3-second slash ack was the first casualty.
        await run_in_threadpool(lambda: tg.handle_update(_conn(), update))
    except Exception:  # noqa: BLE001 — ack anyway so Telegram doesn't retry forever
        traceback.print_exc()
    return {"ok": True}


@app.post("/sync/run")
def sync_run(request: Request):
    """Scheduled pull/flush point. The keepwarm cron hits this every 10 minutes,
    which gives free-tier scheduled sync with no worker process: today it
    flushes quiet chats (any source) into ambient digests; Drive/Gmail pollers
    slot in here."""
    if not _secret_ok(request.headers.get("x-sync-token", "")):
        return JSONResponse({"ok": False}, status_code=403)
    digests = connector_common.run_ambient_digest(_conn()) \
        if (tg.enabled() or sl.enabled()) else 0
    return {"ok": True, "digests": digests}


# --- Slack (Events API + slash commands — see app/connectors/slack.py)

def _slack_guard(body: bytes, request: Request) -> JSONResponse | None:
    """Shared gate for both Slack endpoints: configured, then signed."""
    if not sl.enabled():
        return JSONResponse({"ok": False, "detail": "connector not configured"},
                            status_code=503)
    if not sl.verify_signature(request.headers.get("x-slack-request-timestamp", ""),
                               request.headers.get("x-slack-signature", ""), body):
        return JSONResponse({"ok": False}, status_code=403)
    return None


def _slack_bg(work) -> None:
    try:
        work(_conn())
    except Exception:  # noqa: BLE001 — background failures must not kill the app
        traceback.print_exc()


@app.post("/hooks/slack")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Inbound Events API. The url_verification challenge is answered before
    any gate — it is a liveness probe carrying no data, and echoing it while
    the connector is still dark is what lets the app manifest (which pins this
    URL) apply cleanly before the secrets ever reach the deploy. Everything
    with content sits behind the signature. Events ack immediately and process
    in the background: Slack redelivers after 3s of silence, and dedupe on
    (source, chat, ts) makes those redeliveries no-ops."""
    body = await request.body()
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        return JSONResponse({"ok": False}, status_code=400)
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    if (denied := _slack_guard(body, request)) is not None:
        return denied
    if payload.get("type") == "event_callback":
        background_tasks.add_task(_slack_bg, lambda c: sl.handle_event(c, payload))
    return {"ok": True}


@app.post("/hooks/slack/commands")
async def slack_commands(request: Request, background_tasks: BackgroundTasks):
    """Slash commands (/ask, /teach, /team). Signature is verified over the
    raw form body; slow work acks now and delivers via response_url."""
    body = await request.body()
    if (denied := _slack_guard(body, request)) is not None:
        return denied
    form = dict(urllib.parse.parse_qsl(body.decode()))
    try:
        ack, work = await run_in_threadpool(lambda: sl.handle_command(_conn(), form))
    except Exception:  # noqa: BLE001 — ack anyway; Slack shows raw 500s to users
        traceback.print_exc()
        return {"response_type": "ephemeral", "text": "Something went wrong — try again."}
    if work:
        background_tasks.add_task(_slack_bg, work)
    return ack


@app.post("/search")
def api_search(body: SearchBody):
    results = search(_conn(), body.q, role=body.role, teams=body.teams, top_k=body.top_k)
    return {"results": [{
        "chunk_id": r.chunk_id, "doc_id": r.doc_id, "title": r.title,
        "heading": r.heading, "text": r.text, "team": r.team, "doc_type": r.doc_type,
        "score": round(r.score, 5), "cosine_sim": round(r.cosine_sim, 4),
        "updated_at": f"{r.updated_at:%Y-%m-%d}",
    } for r in results]}


@app.post("/ask")
def api_ask(body: AskBody):
    return ask(_conn(), body.q, role=body.role, teams=body.teams)


@app.post("/ingest")
def api_ingest(body: IngestBody):
    ko = KnowledgeObject(
        id=body.id, title=body.title, body=body.body, source_type=body.source_type,
        source_url=body.source_url, team=body.team, doc_type=body.doc_type,
        owner=body.owner, updated_at=datetime.now(timezone.utc),
        visibility=body.visibility, entities=body.entities, provenance=body.provenance,
    )
    return ingest_document(_conn(), ko)


@app.get("/gaps")
def api_gaps():
    return {"gaps": list_gaps(_conn())}


@app.get("/recipes")
def api_recipes():
    return {"recipes": list_recipes(_conn())}


@app.post("/recipes")
def api_recipe_create(body: RecipeCreateBody):
    slug = save_recipe(_conn(), body.model_dump(), created_by=body.created_by)
    return {"slug": slug, "run_url": f"/recipes/{slug}/run", "ui_url": f"/r/{slug}"}


@app.post("/recipes/{slug}/run")
def api_recipe_run(slug: str, body: RecipeRunBody):
    return run_recipe(_conn(), slug, body.inputs, role=body.role)


# ---------------------------------------------------------------------------- UI

def _page(request: Request, template: str, **ctx):
    ctx.update(request=request, roles=config.ROLES)
    return templates.TemplateResponse(request, template, ctx)


@app.get("/", response_class=HTMLResponse)
def ui_home(request: Request):
    return _page(request, "ask.html", active="ask")


@app.post("/ui/ask", response_class=HTMLResponse)
def ui_ask(request: Request, q: str = Form(...), role: str = Form("everyone")):
    result = ask(_conn(), q, role=role)
    return _page(request, "partials/answer.html", r=result, q=q)


@app.get("/ui/chunk/{chunk_id}", response_class=HTMLResponse)
def ui_chunk(request: Request, chunk_id: int):
    row = _conn().execute(
        """SELECT c.*, d.title, d.team, d.doc_type, d.owner, d.updated_at AS doc_updated,
                  d.source_url FROM chunks c JOIN documents d ON d.id = c.doc_id
           WHERE c.id = %s""", (chunk_id,)).fetchone()
    return _page(request, "partials/chunk.html", c=row)


@app.get("/recipes-ui", response_class=HTMLResponse)
def ui_recipes(request: Request):
    return _page(request, "recipes.html", active="recipes", recipes=list_recipes(_conn()))


@app.get("/r/{slug}", response_class=HTMLResponse)
def ui_recipe(request: Request, slug: str):
    recipe = get_recipe(_conn(), slug)
    if not recipe:
        return RedirectResponse("/recipes-ui")
    return _page(request, "recipe_run.html", active="recipes", recipe=recipe)


@app.post("/r/{slug}", response_class=HTMLResponse)
async def ui_recipe_run(request: Request, slug: str):
    form = dict(await request.form())
    role = form.pop("role", "everyone")
    recipe = get_recipe(_conn(), slug)
    result = await run_in_threadpool(lambda: run_recipe(_conn(), slug, form, role=role))
    return _page(request, "partials/recipe_result.html", r=result, recipe=recipe, inputs=form)


@app.get("/recipes-ui/new", response_class=HTMLResponse)
def ui_recipe_new(request: Request):
    return _page(request, "recipe_new.html", active="recipes")


@app.post("/recipes-ui/new")
def ui_recipe_create(
    request: Request,
    name: str = Form(...), description: str = Form(""),
    inputs: str = Form(""), query: str = Form(...), team_filter: str = Form(""),
    prompt: str = Form(...), creator: str = Form("anonymous"),
):
    input_specs = [{"name": p.strip(), "label": p.strip().replace("_", " ").title(),
                    "type": "text"} for p in inputs.split(",") if p.strip()]
    retrieval = {"query": query, "top_k": 12}
    if team_filter.strip():
        retrieval["filters"] = {"team": [t.strip() for t in team_filter.split(",") if t.strip()]}
    slug = save_recipe(_conn(), {
        "name": name, "description": description, "inputs": input_specs,
        "retrieval": retrieval, "prompt": prompt,
    }, created_by=creator)
    return RedirectResponse(f"/r/{slug}", status_code=303)


@app.post("/ui/capture", response_class=HTMLResponse)
def ui_capture(
    request: Request,
    payer: str = Form(...), procedure: str = Form(...), flag_reason: str = Form(...),
    decision: str = Form(...), reasoning: str = Form(...),
    author: str = Form("specialist"), case_ref: str = Form(""),
):
    result = teach(_conn(), payer=payer, procedure=procedure, flag_reason=flag_reason,
                   decision=decision, reasoning=reasoning, author=author, case_ref=case_ref)
    return _page(request, "partials/capture_done.html", r=result)


@app.get("/gaps-ui", response_class=HTMLResponse)
def ui_gaps(request: Request):
    return _page(request, "gaps.html", active="gaps", gaps=list_gaps(_conn()))


@app.get("/sources", response_class=HTMLResponse)
def ui_sources(request: Request):
    docs = _conn().execute(
        """SELECT d.id, d.title, d.team, d.doc_type, d.owner, d.updated_at, d.visibility,
                  count(c.id) AS n_chunks
           FROM documents d LEFT JOIN chunks c ON c.doc_id = d.id
           GROUP BY d.id ORDER BY d.team, d.doc_type, d.title""").fetchall()
    teams = {}
    for d in docs:
        teams.setdefault(d["team"], []).append(d)
    return _page(request, "sources.html", active="sources", teams=teams)


@app.get("/sources/{doc_id}", response_class=HTMLResponse)
def ui_source(request: Request, doc_id: str):
    doc = _conn().execute("SELECT * FROM documents WHERE id = %s", (doc_id,)).fetchone()
    if doc and doc.get("provenance") and isinstance(doc["provenance"], str):
        doc["provenance"] = json.loads(doc["provenance"])
    return _page(request, "doc.html", active="sources", d=doc)
